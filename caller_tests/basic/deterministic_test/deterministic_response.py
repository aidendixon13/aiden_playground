from __future__ import annotations

import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from openai import OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def _role_to_openai_role(role: Any) -> str:
    """
    Convert a role enum/string to OpenAI-compatible chat role.

    Args:
        role: Enum or string representing the role.

    Returns:
        str: One of "system", "user", "assistant", or a lowercase string best-effort.
    """
    value = getattr(role, "value", role)
    if isinstance(value, str):
        return value.lower()
    return str(value).lower()


def _to_dict(obj: Any) -> Dict[str, Any]:
    """
    Convert an input model or dataclass-like object to a dictionary.

    Supports pydantic v2 (`model_dump`), pydantic v1 (`dict`), plain dicts, and objects with `__dict__`.

    Args:
        obj: The object to convert.

    Returns:
        dict: A dictionary representation of the object.
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()  # type: ignore[attr-defined]
    if hasattr(obj, "dict"):
        return obj.dict()  # type: ignore[attr-defined]
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {}


def _serialize_config_to_messages(config: Any, variables: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Turn a CallerChatConfig's prompt templates into raw OpenAI message dicts.

    Args:
        config: Caller configuration object with `prompt_messages`.
        variables: Mapping used to `.format(**variables)` the prompt templates.

    Returns:
        list[dict[str, str]]: List of {"role", "content"} messages.
    """
    messages: List[Dict[str, str]] = []
    for pm in getattr(config, "prompt_messages", []) or []:
        role = _role_to_openai_role(getattr(pm, "role", "user"))
        prompt_template = getattr(pm, "prompt", "")
        if not isinstance(prompt_template, str):
            prompt_template = str(prompt_template)
        try:
            content = prompt_template.format(**variables)
        except Exception:
            content = prompt_template
        messages.append({"role": role, "content": content})
    return messages


def _extract_model_name(config: Any, default: str = "gpt-4.1") -> str:
    """
    Resolve the OpenAI model name from a caller config.

    Args:
        config: Caller configuration object potentially holding `llm_init_kwargs` with `model_name`.
        default: Fallback model name.

    Returns:
        str: The model name string.
    """
    kwargs = getattr(config, "llm_init_kwargs", {}) or {}
    model_name = kwargs.get("model_name", default)
    # Handle enums like OpenAIModels.O4_MINI by reading `.value`
    value = getattr(model_name, "value", model_name)
    return str(value)


def _add_additional_properties_false(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively add 'additionalProperties: false' to all objects in the schema.

    OpenAI's structured outputs require this for strict mode.

    Args:
        schema: The schema dictionary to modify.

    Returns:
        dict: Modified schema with additionalProperties set.
    """
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
        for key, value in schema.items():
            if isinstance(value, dict):
                _add_additional_properties_false(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _add_additional_properties_false(item)
    return schema


def _pydantic_to_openai_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Convert a Pydantic model to OpenAI's json_schema format.

    Args:
        model: Pydantic model class to convert.

    Returns:
        dict: Schema in OpenAI's expected format with name, description, schema, and strict.
    """
    schema = model.model_json_schema()
    # Ensure additionalProperties: false is set for all objects (required by OpenAI strict mode)
    schema = _add_additional_properties_false(schema)
    return {
        "name": model.__name__,
        "description": model.__doc__ or f"Structured output for {model.__name__}",
        "schema": schema,
        "strict": True,
    }


def find_low_confidence_tokens(choice_logprobs, threshold: float = 0.001) -> List[Dict[str, Any]]:
    """
    Find token positions where the probability difference between top and bottom
    candidates is less than the threshold.

    Args:
        choice_logprobs: The logprobs object from the API response.
        threshold: Probability difference threshold (default 0.001).

    Returns:
        list[dict]: List of low-confidence tokens with their details.
    """
    low_confidence_tokens = []

    for idx, token_info in enumerate(choice_logprobs.content):
        if not token_info.top_logprobs or len(token_info.top_logprobs) < 2:
            continue

        # Get probabilities for all candidates
        probs = [math.exp(cand.logprob) for cand in token_info.top_logprobs if cand.logprob is not None]

        if len(probs) >= 2:
            top_prob = max(probs)
            bottom_prob = min(probs)
            prob_diff = top_prob - bottom_prob

            if prob_diff < threshold:
                low_confidence_tokens.append(
                    {
                        "position": idx,
                        "token": token_info.token,
                        "top_prob": top_prob,
                        "bottom_prob": bottom_prob,
                        "difference": prob_diff,
                        "candidates": [(cand.token, math.exp(cand.logprob)) for cand in token_info.top_logprobs],
                    }
                )

    return low_confidence_tokens


def run_openai_chat_from_config(
    caller_config: Any,
    input_model: Any,
    *,
    output_schema: Optional[Type[T]] = None,
    temperature: Optional[float] = None,
    seed: Optional[int] = None,
    max_tokens: Optional[int] = None,
    n: Optional[int] = None,
    return_logprobs_info: bool = False,
    enable_logprobs: bool = True,
) -> Union[str, T, tuple]:
    """
    Run a single OpenAI Chat Completions call using a `CallerChatConfig` and an input model.

    This function serializes the config's prompt templates into OpenAI-style `messages`,
    formats placeholders with values from the provided `input_model`, and issues a
    `chat.completions.create` request. It returns the assistant's message content.

    Args:
        caller_config: The `CallerChatConfig` describing prompts and model settings.
        input_model: Pydantic model/dict with fields used to format prompt placeholders.
        output_schema: Optional Pydantic model class for structured outputs. If provided,
                      response will be validated against this schema and returned as instance.
        temperature: Optional override for sampling temperature. Falls back to config.
        seed: Optional deterministic seed for sampling. If not provided, omitted.
        max_tokens: Optional override for max tokens. Falls back to config if available.
        n: Optional number of completions to generate. If > 1, returns most common response.
        return_logprobs_info: If True, returns tuple of (result, low_conf_tokens).
        enable_logprobs: If True, requests logprobs (automatically disabled for O-series models).

    Returns:
        Union[str, BaseModel, tuple]: If output_schema provided, returns validated Pydantic instance.
                                       Otherwise returns raw string content.
                                       If n > 1, returns the most common response among all completions.
                                       If return_logprobs_info=True, returns tuple of (result, low_conf_tokens).

    Raises:
        Exception: Propagates any errors from the OpenAI API call.
    """
    client = OpenAI()

    variables = _to_dict(input_model)
    messages = _serialize_config_to_messages(caller_config, variables)

    model_name = _extract_model_name(caller_config)
    kwargs = getattr(caller_config, "llm_init_kwargs", {}) or {}

    request_kwargs: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
    }

    # Add structured output schema if provided
    if output_schema is not None:
        schema_dict = _pydantic_to_openai_schema(output_schema)
        request_kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": schema_dict,
        }

    # Forward optional reasoning settings from config
    # Accept either a full dict under "reasoning" or a shorthand string under "reasoning_effort"
    reasoning_cfg: Optional[Dict[str, Any]] = None
    if isinstance(kwargs.get("reasoning"), dict):
        reasoning_cfg = kwargs.get("reasoning")  # type: ignore[assignment]
    else:
        effort = kwargs.get("reasoning_effort")
        if isinstance(effort, str) and effort:
            reasoning_cfg = {"effort": effort}
    if reasoning_cfg:
        request_kwargs["reasoning_effort"] = reasoning_cfg.get("effort", "low")
    if seed is not None:
        request_kwargs["seed"] = seed
    if n is not None and n > 1:
        request_kwargs["n"] = n

    # Enable logprobs to detect low-confidence tokens (if model supports it)
    # O-series models (o1, o3, o4) don't support logprobs
    model_supports_logprobs = not any(x in model_name.lower() for x in ["o1", "o3", "o4"])
    if enable_logprobs and model_supports_logprobs:
        request_kwargs["logprobs"] = True
        request_kwargs["top_logprobs"] = 5

    start = time.time()
    chat = client.chat.completions.create(**request_kwargs)

    if not chat.choices:
        return "" if output_schema is None else output_schema()  # type: ignore

    # If n > 1, aggregate choices and return the most common response
    if n is not None and n > 1:
        texts: List[str] = []
        for choice in chat.choices:
            content = getattr(getattr(choice, "message", None), "content", None)
            texts.append(content or "")

        # Normalize for counting but preserve original earliest occurrence
        normalized = [t.strip() for t in texts]
        counts = Counter(normalized)
        # Determine winner with tie-breaker on first occurrence index
        best = None
        best_count = -1
        best_index = len(normalized)
        for idx, txt in enumerate(normalized):
            c = counts[txt]
            if c > best_count or (c == best_count and idx < best_index):
                best = txt
                best_count = c
                best_index = idx

        end = time.time()
        print(f"Latency: {end - start:.2f}s (n={n}, most common appeared {best_count} times)")

        # Analyze low-confidence tokens from the first choice
        low_conf_tokens = []
        if enable_logprobs and model_supports_logprobs and chat.choices[0].logprobs:
            low_conf_tokens = find_low_confidence_tokens(chat.choices[0].logprobs, threshold=0.001)
            if low_conf_tokens:
                print(f"⚠️  Found {len(low_conf_tokens)} low-confidence token(s) (diff < 0.001)")

        # Get the winning text
        final_text = texts[best_index] if best is not None else texts[0]

        # Parse into Pydantic model if schema provided
        if output_schema is not None:
            try:
                parsed = json.loads(final_text)
                result = output_schema(**parsed)  # type: ignore
            except Exception as e:
                print(f"Warning: Failed to parse into {output_schema.__name__}: {e}")
                result = final_text  # type: ignore
        else:
            result = final_text

        if return_logprobs_info:
            return (result, low_conf_tokens)
        return result
    else:
        # Single response mode
        end = time.time()
        print(f"Latency: {end - start:.2f}s (single response)")

        # Analyze low-confidence tokens
        low_conf_tokens = []
        if enable_logprobs and model_supports_logprobs and chat.choices[0].logprobs:
            low_conf_tokens = find_low_confidence_tokens(chat.choices[0].logprobs, threshold=0.001)
            if low_conf_tokens:
                print(f"⚠️  Found {len(low_conf_tokens)} low-confidence token(s) (diff < 0.001)")

        content = getattr(getattr(chat.choices[0], "message", None), "content", None)
        final_text = content or ""

        # Parse into Pydantic model if schema provided
        if output_schema is not None:
            try:
                parsed = json.loads(final_text)
                result = output_schema(**parsed)  # type: ignore
            except Exception as e:
                print(f"Warning: Failed to parse into {output_schema.__name__}: {e}")
                result = final_text  # type: ignore
        else:
            result = final_text

        if return_logprobs_info:
            return (result, low_conf_tokens)
        return result


def main(
    caller_config: Any,
    input_model: Any,
    *,
    output_schema: Optional[Type[T]] = None,
    temperature: Optional[float] = None,
    seed: Optional[int] = None,
    max_tokens: Optional[int] = None,
    n: Optional[int] = None,
) -> Union[str, T]:
    """
    Entry point to run an OpenAI Chat Completion from a `CallerChatConfig` and inputs.

    Args:
        caller_config: The `CallerChatConfig` object to drive prompts and model config.
        input_model: Dict or Pydantic model providing values for prompt placeholders.
        output_schema: Optional Pydantic model class for structured outputs.
        temperature: Optional override for sampling temperature.
        seed: Optional seed for deterministic sampling.
        max_tokens: Optional override for maximum output tokens.
        n: Optional number of completions to generate. If > 1, returns most common response.

    Returns:
        Union[str, BaseModel]: If output_schema provided, returns validated Pydantic instance.
                               Otherwise returns raw string content.
    """
    return run_openai_chat_from_config(
        caller_config=caller_config,
        input_model=input_model,
        output_schema=output_schema,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
        n=n,
    )


def load_test_cases(json_path: str) -> List[Dict[str, Any]]:
    """
    Load test cases from a JSON file.

    Args:
        json_path: Path to the JSON file containing test cases.

    Returns:
        list[dict]: List of test case dictionaries.
    """
    with open(json_path, "r") as f:
        data = json.load(f)
    return data.get("test_cases", [])


def compare_time_references(predicted: List[str], expected: List[str]) -> bool:
    """
    Compare predicted time references with expected ones.

    Args:
        predicted: List of predicted time reference strings.
        expected: List of expected time reference strings.

    Returns:
        bool: True if the sets match exactly, False otherwise.
    """
    return set(predicted) == set(expected)


def evaluate_on_dataset(
    caller_config: Any,
    test_cases: List[Dict[str, Any]],
    output_schema: Type[T],
    *,
    current_month: str = "2025M8",
    fiscal_year_start: str = "January",
    selected_view_members: str = "No specific view members selected",
    selected_dimension_members: str = "",
    seed: Optional[int] = None,
    n: Optional[int] = None,
    runs_per_test: int = 1,
) -> Dict[str, Any]:
    """
    Evaluate the caller on a dataset of test cases.

    Args:
        caller_config: The caller configuration to test.
        test_cases: List of test case dictionaries with 'query', 'time_reference', 'expected_members'.
        output_schema: Pydantic model class for structured outputs.
        current_month: Current month for all test cases.
        fiscal_year_start: Fiscal year start for all test cases.
        selected_view_members: Selected view members for all test cases.
        selected_dimension_members: Selected dimension members for all test cases.
        seed: Optional seed for deterministic sampling.
        n: Optional number of completions to aggregate.
        runs_per_test: Number of times to run each test case (for consistency testing).

    Returns:
        dict: Evaluation results with accuracy, correct count, total count, latencies, and details.
    """
    results = []
    correct = 0
    total_runs = 0
    latencies = []

    # Track consistency per test case
    test_case_stats = []

    for i, test_case in enumerate(test_cases, 1):
        query = test_case.get("query", "")
        time_reference = test_case.get("time_reference", "")
        expected_members = test_case.get("expected_members", [])

        input_data = {
            "current_month": current_month,
            "fiscal_year_start": fiscal_year_start,
            "selected_view_members": selected_view_members,
            "selected_dimension_members": selected_dimension_members,
            "user_input": query,
            "time_reference": time_reference,
        }

        # Run the test case multiple times
        run_results = []
        run_latencies = []
        run_predictions = []

        for run_num in range(1, runs_per_test + 1):
            try:
                start_time = time.time()
                result = main(
                    caller_config=caller_config,
                    input_model=input_data,
                    output_schema=output_schema,
                    seed=seed,
                    n=n,
                )
                latency = time.time() - start_time
                latencies.append(latency)
                run_latencies.append(latency)

                if hasattr(result, "time_references"):
                    predicted_members = result.time_references
                else:
                    predicted_members = []

                run_predictions.append(predicted_members)
                is_correct = compare_time_references(predicted_members, expected_members)

                run_results.append(
                    {
                        "run": run_num,
                        "predicted": predicted_members,
                        "correct": is_correct,
                        "latency": latency,
                    }
                )

                if is_correct:
                    correct += 1
                total_runs += 1

                # Print progress
                status = "✓" if is_correct else "✗"
                if runs_per_test > 1:
                    print(f"[{i}/{len(test_cases)}] Run {run_num}/{runs_per_test} {status} {time_reference} ({latency:.2f}s)")
                else:
                    print(f"[{i}/{len(test_cases)}] {status} {time_reference} ({latency:.2f}s)")

            except Exception as e:
                print(f"[{i}/{len(test_cases)}] Run {run_num}/{runs_per_test} ERROR: {time_reference} - {str(e)}")
                run_results.append(
                    {
                        "run": run_num,
                        "predicted": [],
                        "correct": False,
                        "error": str(e),
                    }
                )
                total_runs += 1

        # Calculate consistency metrics for this test case
        correct_count = sum(1 for r in run_results if r.get("correct", False))
        consistency = correct_count / runs_per_test if runs_per_test > 0 else 0.0

        # Check if all predictions are identical (full consistency)
        unique_predictions = set(tuple(sorted(p)) for p in run_predictions if p)
        is_deterministic = len(unique_predictions) <= 1

        test_case_result = {
            "test_case_number": i,
            "query": query,
            "time_reference": time_reference,
            "expected": expected_members,
            "runs": run_results,
            "consistency": consistency,
            "correct_count": correct_count,
            "total_runs": runs_per_test,
            "is_deterministic": is_deterministic,
            "unique_predictions": len(unique_predictions),
            "avg_latency": sum(run_latencies) / len(run_latencies) if run_latencies else 0.0,
        }

        results.append(test_case_result)
        test_case_stats.append(
            {
                "test_case": i,
                "consistency": consistency,
                "is_deterministic": is_deterministic,
            }
        )

    accuracy = correct / total_runs if total_runs > 0 else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    min_latency = min(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0

    # Calculate overall consistency metrics
    avg_consistency = sum(s["consistency"] for s in test_case_stats) / len(test_case_stats) if test_case_stats else 0.0
    deterministic_count = sum(1 for s in test_case_stats if s["is_deterministic"])
    deterministic_rate = deterministic_count / len(test_case_stats) if test_case_stats else 0.0

    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total_runs,
        "avg_latency": avg_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,
        "runs_per_test": runs_per_test,
        "avg_consistency": avg_consistency,
        "deterministic_rate": deterministic_rate,
        "results": results,
    }


if __name__ == "__main__":
    # Evaluation mode on full test dataset
    try:
        from wernicke.agents.rubix.cube_view.subgraph_orchestrators.theme_extraction_orchestrator.callers.time_resolve_caller import (
            TimeResolveChatConfig,
        )
        from wernicke.agents.rubix.cube_view.subgraph_orchestrators.theme_extraction_orchestrator.models import TimeResolveOutput
    except Exception:
        TimeResolveChatConfig = None  # type: ignore[assignment]
        TimeResolveOutput = None  # type: ignore[assignment]

    if TimeResolveChatConfig is not None and TimeResolveOutput is not None:
        # Path to test cases JSON
        test_json_path = (
            Path(__file__).parent.parent.parent.parent.parent.parent
            / "source"
            / "wernicke"
            / "tests"
            / "evaluations"
            / "finance_analyst"
            / "deprecated"
            / "test_cases"
            / "time_resolve_caller.json"
        )

        if test_json_path.exists():
            print(f"Loading test cases from: {test_json_path}")
            test_cases = load_test_cases(str(test_json_path))
            test_cases = [test_cases[10]]
            print(f"Loaded {len(test_cases)} test cases\n")

            # Evaluation 1: Single response mode
            print("=" * 80)
            print("EVALUATION 1: Single Response Mode (no aggregation)")
            print("=" * 80)
            RUNS_PER_TEST = 10  # Configure how many times to run each test
            eval_single = evaluate_on_dataset(
                caller_config=TimeResolveChatConfig,
                test_cases=test_cases,
                output_schema=TimeResolveOutput,
                current_month="2025M8",
                fiscal_year_start="January",
                selected_view_members="No specific view members selected",
                seed=1,
                n=None,
                runs_per_test=RUNS_PER_TEST,
            )
            print(f"\n📊 Single Response Results:")
            print(f"   Accuracy: {eval_single['accuracy']:.2%}")
            print(f"   Correct: {eval_single['correct']}/{eval_single['total']}")
            print(f"   Runs per test: {eval_single['runs_per_test']}")
            print(f"   Avg Consistency: {eval_single['avg_consistency']:.2%}")
            print(f"   Deterministic Rate: {eval_single['deterministic_rate']:.2%}")
            print(f"   Avg Latency: {eval_single['avg_latency']:.2f}s")
            print(f"   Min Latency: {eval_single['min_latency']:.2f}s")
            print(f"   Max Latency: {eval_single['max_latency']:.2f}s")

            # Evaluation 2: Aggregated mode (n=5)
            print("\n" + "=" * 80)
            print("EVALUATION 2: Aggregated Mode (n=5, most common response)")
            print("=" * 80)
            eval_aggregated = evaluate_on_dataset(
                caller_config=TimeResolveChatConfig,
                test_cases=test_cases,
                output_schema=TimeResolveOutput,
                current_month="2025M8",
                fiscal_year_start="January",
                selected_view_members="No specific view members selected",
                seed=1,
                n=5,
                runs_per_test=RUNS_PER_TEST,
            )
            print(f"\n📊 Aggregated Response Results:")
            print(f"   Accuracy: {eval_aggregated['accuracy']:.2%}")
            print(f"   Correct: {eval_aggregated['correct']}/{eval_aggregated['total']}")
            print(f"   Runs per test: {eval_aggregated['runs_per_test']}")
            print(f"   Avg Consistency: {eval_aggregated['avg_consistency']:.2%}")
            print(f"   Deterministic Rate: {eval_aggregated['deterministic_rate']:.2%}")
            print(f"   Avg Latency: {eval_aggregated['avg_latency']:.2f}s")
            print(f"   Min Latency: {eval_aggregated['min_latency']:.2f}s")
            print(f"   Max Latency: {eval_aggregated['max_latency']:.2f}s")

            # Summary comparison
            print("\n" + "=" * 80)
            print("SUMMARY COMPARISON")
            print("=" * 80)
            print(
                f"Single Response:    {eval_single['accuracy']:.2%} ({eval_single['correct']}/{eval_single['total']}) | "
                f"Consistency: {eval_single['avg_consistency']:.2%} | Deterministic: {eval_single['deterministic_rate']:.2%} | "
                f"Avg: {eval_single['avg_latency']:.2f}s"
            )
            print(
                f"Aggregated (n=5):   {eval_aggregated['accuracy']:.2%} ({eval_aggregated['correct']}/{eval_aggregated['total']}) | "
                f"Consistency: {eval_aggregated['avg_consistency']:.2%} | Deterministic: {eval_aggregated['deterministic_rate']:.2%} | "
                f"Avg: {eval_aggregated['avg_latency']:.2f}s"
            )

            improvement = eval_aggregated["accuracy"] - eval_single["accuracy"]
            latency_diff = eval_aggregated["avg_latency"] - eval_single["avg_latency"]
            consistency_diff = eval_aggregated["avg_consistency"] - eval_single["avg_consistency"]

            print("\n💡 Key Findings:")
            if improvement > 0:
                print(f"   ✅ Aggregation improved accuracy by {improvement:.2%}")
            elif improvement < 0:
                print(f"   ⚠️  Aggregation decreased accuracy by {abs(improvement):.2%}")
            else:
                print(f"   ➖ No change in accuracy")

            if consistency_diff > 0:
                print(f"   ✅ Aggregation improved consistency by {consistency_diff:.2%}")
            elif consistency_diff < 0:
                print(f"   ⚠️  Aggregation decreased consistency by {abs(consistency_diff):.2%}")
            else:
                print(f"   ➖ No change in consistency")

            print(f"   ⏱️  Latency impact: {latency_diff:+.2f}s ({latency_diff/eval_single['avg_latency']*100:+.1f}%)")

            # Per-test consistency details
            print("\n" + "=" * 80)
            print("PER-TEST CONSISTENCY DETAILS")
            print("=" * 80)
            for result in eval_single["results"]:
                tc_num = result["test_case_number"]
                consistency = result["consistency"]
                is_det = "✓" if result["is_deterministic"] else "✗"
                unique_preds = result["unique_predictions"]
                print(f"Test {tc_num}: {consistency:.1%} consistency | Deterministic: {is_det} | Unique predictions: {unique_preds}")
                if not result["is_deterministic"] and result["runs"]:
                    print(f"  Predictions across {len(result['runs'])} runs:")
                    for run in result["runs"][:5]:  # Show first 5 runs
                        status = "✓" if run.get("correct", False) else "✗"
                        print(f"    Run {run['run']}: {status} {run.get('predicted', [])}")
                    if len(result["runs"]) > 5:
                        print(f"    ... and {len(result['runs']) - 5} more runs")

            # Show failed cases for both modes
            print("\n" + "=" * 80)
            print("FAILED CASES (Single Response)")
            print("=" * 80)
            for result in eval_single["results"]:
                if result["consistency"] < 1.0:  # At least one run failed
                    print(f"\n❌ Test {result['test_case_number']}: {result['time_reference']}")
                    print(f"   Expected: {result['expected']}")
                    print(f"   Consistency: {result['consistency']:.1%} ({result['correct_count']}/{result['total_runs']} correct)")
                    if result["runs"]:
                        print(f"   Predictions across runs:")
                        for run in result["runs"]:
                            status = "✓" if run.get("correct", False) else "✗"
                            pred = run.get("predicted", [])
                            print(f"     Run {run['run']}: {status} {pred}")
                            if "error" in run:
                                print(f"       Error: {run['error']}")

            print("\n" + "=" * 80)
            print("FAILED CASES (Aggregated n=5)")
            print("=" * 80)
            for result in eval_aggregated["results"]:
                if result["consistency"] < 1.0:  # At least one run failed
                    print(f"\n❌ Test {result['test_case_number']}: {result['time_reference']}")
                    print(f"   Expected: {result['expected']}")
                    print(f"   Consistency: {result['consistency']:.1%} ({result['correct_count']}/{result['total_runs']} correct)")
                    if result["runs"]:
                        print(f"   Predictions across runs:")
                        for run in result["runs"]:
                            status = "✓" if run.get("correct", False) else "✗"
                            pred = run.get("predicted", [])
                            print(f"     Run {run['run']}: {status} {pred}")
                            if "error" in run:
                                print(f"       Error: {run['error']}")

        else:
            print(f"Test JSON file not found at: {test_json_path}")
            print("Using simple demo instead...")

            demo_inputs = {
                "current_month": "2025M8",
                "fiscal_year_start": "January",
                "selected_view_members": "No specific view members selected",
                "user_input": "Show me how our gross margin for the Acme Nexus Series product line has trended over the last 16 months?",
                "time_reference": "last 16 months",
            }

            print("=== Single Response Demo ===")
            result = main(
                caller_config=TimeResolveChatConfig,
                input_model=demo_inputs,
                output_schema=TimeResolveOutput,
                seed=1,
            )
            print(f"Result: {result}")

    else:
        print("Demo skipped: TimeResolveChatConfig or TimeResolveOutput not importable in this environment.")

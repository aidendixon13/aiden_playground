from __future__ import annotations

import time
from collections import Counter
from typing import Any, Dict, List, Optional

from openai import OpenAI


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


def run_openai_chat_from_config(
    caller_config: Any,
    input_model: Any,
    *,
    temperature: Optional[float] = None,
    seed: Optional[int] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Run a single OpenAI Chat Completions call using a `CallerChatConfig` and an input model.

    This function serializes the config's prompt templates into OpenAI-style `messages`,
    formats placeholders with values from the provided `input_model`, and issues a
    `chat.completions.create` request. It returns the assistant's message content.

    Args:
        caller_config: The `CallerChatConfig` describing prompts and model settings.
        input_model: Pydantic model/dict with fields used to format prompt placeholders.
        temperature: Optional override for sampling temperature. Falls back to config.
        seed: Optional deterministic seed for sampling. If not provided, omitted.
        max_tokens: Optional override for max tokens. Falls back to config if available.

    Returns:
        str: The assistant's response content (empty string if not present).

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
        request_kwargs["reasoning_effort"] = "minimal"
    if seed is not None:
        request_kwargs["seed"] = seed

    request_kwargs["n"] = 5

    start = time.time()
    chat = client.chat.completions.create(**request_kwargs)

    if not chat.choices:
        return ""

    # Aggregate n choices and return the most common response
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
    print(f"Latency: {end - start:.2f}s")

    # Return the original (un-normalized) text corresponding to the winning normalized value
    return texts[best_index] if best is not None else texts[0]


def main(
    caller_config: Any,
    input_model: Any,
    *,
    temperature: Optional[float] = None,
    seed: Optional[int] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Entry point to run an OpenAI Chat Completion from a `CallerChatConfig` and inputs.

    Args:
        caller_config: The `CallerChatConfig` object to drive prompts and model config.
        input_model: Dict or Pydantic model providing values for prompt placeholders.
        temperature: Optional override for sampling temperature.
        seed: Optional seed for deterministic sampling.
        max_tokens: Optional override for maximum output tokens.

    Returns:
        str: Assistant message content.
    """
    return run_openai_chat_from_config(
        caller_config=caller_config,
        input_model=input_model,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
    )


if __name__ == "__main__":
    # Minimal demo usage with TimeResolveChatConfig
    try:
        from wernicke.agents.rubix.cube_view.subgraph_orchestrators.theme_extraction_orchestrator.callers.time_resolve_caller import (
            TimeResolveChatConfig,
        )
    except Exception:
        TimeResolveChatConfig = None  # type: ignore[assignment]

    demo_inputs = {
        "current_month": "2025M8",
        "fiscal_year_start": "January",
        "selected_view_members": "No specific view members selected",
        "selected_dimension_members": "\n<Dimension Member>\nName: Expenses\nDescription: Expenses\nType: Account\n</Dimension Member>\n<Dimension Member>\nName: ExternalReporting\nDescription: External Reporting\nType: Department\n</Dimension Member>",
        "user_input": "Show me expenses for 2024 quarters and the year total for the UD1 - external reporting",
        "time_reference": "2024 quarters",
    }

    if TimeResolveChatConfig is not None:
        for i in range(10):
            print(
                main(
                    caller_config=TimeResolveChatConfig,
                    input_model=demo_inputs,
                    seed=1,
                )
            )
        #  ['2024Q1', '2024Q2', '2024Q3', '2024Q4']
    else:
        print("Demo skipped: TimeResolveChatConfig not importable in this environment.")

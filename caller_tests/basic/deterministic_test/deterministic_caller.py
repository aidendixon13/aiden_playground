import math
from typing import Any, Dict, List

from openai import OpenAI

# Import a real caller config and convert it to raw OpenAI messages
from wernicke.agents.rubix.cube_view.subgraph_orchestrators.theme_extraction_orchestrator.callers.time_resolve_caller import TimeResolveChatConfig

client = OpenAI()  # requires OPENAI_API_KEY

schema = {
    "name": "TimeResolveOutput",
    "description": "Structured output for time resolution containing resolved time dimension members.",
    "schema": {
        "type": "object",
        "properties": {
            "time_references": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The time references that were resolved to dimension members.",
            }
        },
        "required": ["time_references"],
        "additionalProperties": False,
    },
    "strict": True,
}


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


# Example variable values for TimeResolveChatConfig prompt templates
_variables = {
    "current_month": "2025M8",
    "fiscal_year_start": "January",
    "selected_view_members": "No Specific View Members Selected",
    "user_input": "Show me how our gross margin for the Acme Nexus Series product line has trended over the last 16 months?",
    "time_reference": "last 16 months",
}

messages = _serialize_config_to_messages(TimeResolveChatConfig, _variables)
model = "gpt-4.1"
print("=== Responses API (Structured Outputs) ===")
resp_responses = client.responses.create(
    model=model,
    input=messages,
    text={"format": {"type": "json_schema", **schema}},
    temperature=0,
    max_output_tokens=200,
)
print(resp_responses.output_text)  # JSON string

print("\n=== Chat Completions API (Structured + Logprobs) ===")


def find_low_confidence_tokens(choice_logprobs, threshold: float = 0.001) -> list[dict]:
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


for i in range(10):
    chat = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_schema", "json_schema": schema},
        temperature=0,
        max_tokens=200,
        logprobs=True,
        top_logprobs=5,
    )

    # Print the structured output
    print(f"\n--- Run {i+1} ---")
    full_text = chat.choices[0].message.content
    print(full_text)

    # For the first run, show detailed token analysis
    if i == 0:
        print("\n=== Tokens ===")
        _tokens_seq = chat.choices[0].logprobs.content
        _tokens_list = [t.token for t in _tokens_seq]
        print(_tokens_list)

        print("\n=== Top-5 candidates per token ===")
        for idx, token_info in enumerate(chat.choices[0].logprobs.content):
            token = token_info.token
            token_logprob = token_info.logprob
            token_prob = math.exp(token_logprob)
            print(f"Token {idx}: '{token}'  logprob={token_logprob:.6f}  p={token_prob:.6e}")

            if token_info.top_logprobs:
                for rank, cand in enumerate(token_info.top_logprobs, start=1):
                    cand_logprob = cand.logprob
                    cand_prob = math.exp(cand_logprob)
                    print(f"  {rank}. '{cand.token}'  logprob={cand_logprob:.6f}  p={cand_prob:.6e}")
            else:
                print("  (no top_logprobs available)")

    # Find low-confidence tokens (where top and bottom differ by < 0.001)
    low_conf_tokens = find_low_confidence_tokens(chat.choices[0].logprobs, threshold=0.001)

    if low_conf_tokens:
        print(f"\n⚠️  Found {len(low_conf_tokens)} low-confidence token(s) (diff < 0.001):")
        for token_data in low_conf_tokens:
            print(f"  Position {token_data['position']}: '{token_data['token']}'")
            print(f"    Top prob: {token_data['top_prob']:.6f}, Bottom prob: {token_data['bottom_prob']:.6f}")
            print(f"    Difference: {token_data['difference']:.6f}")
            print(f"    Candidates: {token_data['candidates'][:3]}")  # Show top 3
    else:
        print(f"\n✓ No low-confidence tokens found (all diffs >= 0.001)")

print("\n=== Analysis Complete ===")
print("Low-confidence tokens (prob difference < 0.001) indicate positions where")
print("the model has uncertainty between multiple candidate tokens.")

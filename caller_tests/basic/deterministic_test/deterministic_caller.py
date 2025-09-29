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
    "current_month": "2025M9",
    "fiscal_year_start": "January",
    "selected_view_members": "Periodic",
    "user_input": "Show me my 2025 YTD revenue.",
    "time_reference": "2025 YTD",
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


def _extract_yes_no_probs(choice_logprobs) -> tuple[float | None, float | None]:
    """
    Scan all token positions' top candidates and capture probabilities for 'yes' and 'no'.

    Returns:
        (p_yes, p_no): probabilities if found among top candidates, else None.
    """
    p_yes = None
    p_no = None
    for token_info in choice_logprobs.content:
        if not token_info.top_logprobs:
            continue
        for cand in token_info.top_logprobs:
            tok = (cand.token or "").strip().strip('"').lower()
            if tok == "yes":
                p = math.exp(cand.logprob) if cand.logprob is not None else None
                if p is not None:
                    p_yes = p if p_yes is None else max(p_yes, p)
            elif tok == "no":
                p = math.exp(cand.logprob) if cand.logprob is not None else None
                if p is not None:
                    p_no = p if p_no is None else max(p_no, p)
    return p_yes, p_no


run_summaries: list[tuple[float | None, float | None]] = []

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

    # Print the structured output once for visibility
    print(f"\n--- Run {i+1} ---")
    full_text = chat.choices[0].message.content
    print(full_text)

    # For the first run, also show tokens and candidates to inspect
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

    p_yes, p_no = _extract_yes_no_probs(chat.choices[0].logprobs)
    run_summaries.append((p_yes, p_no))
    print(f"yes p: {p_yes if p_yes is not None else 'N/A'} | no p: {p_no if p_no is not None else 'N/A'}")

print("\n=== Summary over 5 runs (max prob seen across positions per run) ===")
for i, (p_yes, p_no) in enumerate(run_summaries, start=1):
    print(f"Run {i}: yes p={p_yes if p_yes is not None else 'N/A'} | no p={p_no if p_no is not None else 'N/A'}")

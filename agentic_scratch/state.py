"""
==============================================================================
Name: state
Author: AI Assistant
Date: 10/20/2025
Description: State model for the agentic scratch orchestrator.
==============================================================================
"""

from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import ToolMessage
from pydantic import Field

from wernicke.engines.llm.llm_callers.models import Conversation, ToolCallAction
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.models import BaseGraphState


def tool_results_reducer(left: Any, right: Any) -> List[Any]:
    """
    Reducer for combining tool results from parallel tool execution.

    Args:
        left (Any): The existing list of tool results.
        right (Any): Either a list of new tool results to append, or a dict with
                     {"kind": "rewrite", "value": [...]} to replace the entire list.

    Returns:
        List[Any]: The combined or rewritten list of tool results.
    """
    left = left or []
    if isinstance(right, dict) and right.get("kind") == "rewrite":
        return right["value"]
    return left + right


class AgenticScratchState(BaseGraphState):
    """
    State model for the agentic scratch orchestrator.

    Attributes:
        user_input (str): The user's input query.
        conversation (Optional[Conversation]): The conversation state of the agentic loop.
        tool_calls (List[ToolCallAction]): The tool calls made by the agent.
        tool_results (Annotated[List[ToolMessage], tool_results_reducer]): The tool results.
        task_data (Dict[str, Any]): Dictionary to store any task-specific data.
        final_output (Optional[str]): The final output to return to the user.
    """

    user_input: str
    conversation: Optional[Conversation] = None
    tool_calls: List[ToolCallAction] = Field(default_factory=list)
    tool_results: Annotated[List[ToolMessage], tool_results_reducer] = Field(default_factory=list)
    task_data: Dict[str, Any] = Field(default_factory=dict)
    final_output: Optional[str] = None

"""
==============================================================================
Name: search_tool_node
Author: AI Assistant
Date: 10/20/2025
Description: Node implementation for the search tool.
==============================================================================
"""

from typing import Any, Dict

from langchain_core.messages import ToolMessage
from pydantic import BaseModel, Field

from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.models import BaseGraphState
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.node_types.base import INode
from wernicke.shared.decorators.wernicke_langsmith_tracing import wernicke_ls_traceable


class SearchToolState(BaseGraphState):
    """
    State for the search tool node.

    Attributes:
        tool_call_id (str): The tool call ID.
        query (str): The search query.
    """

    tool_call_id: str
    query: str


class SearchToolNode(INode):
    """
    Node that executes the search tool logic.
    """

    name = "SearchToolNode"

    @wernicke_ls_traceable
    async def execute(self, graph_state: SearchToolState) -> Dict[str, Any]:
        """
        Execute the search tool logic.

        Args:
            graph_state (SearchToolState): The current state.

        Returns:
            Dict[str, Any]: Updated state with tool results.
        """
        # Mock search results
        results = [
            f"Result 1 for '{graph_state.query}'",
            f"Result 2 for '{graph_state.query}'",
            f"Result 3 for '{graph_state.query}'",
        ]

        formatted_results = "\n".join([f"{i+1}. {result}" for i, result in enumerate(results)])
        content = f"Search results for '{graph_state.query}':\n{formatted_results}"

        tool_message = ToolMessage(
            content=content,
            tool_call_id=graph_state.tool_call_id,
            artifact={"results": results, "query": graph_state.query},
        )

        return {"tool_results": [tool_message]}

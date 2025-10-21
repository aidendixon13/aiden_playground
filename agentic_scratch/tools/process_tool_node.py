"""
==============================================================================
Name: process_tool_node
Author: AI Assistant
Date: 10/20/2025
Description: Node implementation for the process tool.
==============================================================================
"""

from typing import Any, Dict

from langchain_core.messages import ToolMessage

from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.models import BaseGraphState
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.node_types.base import INode
from wernicke.shared.decorators.wernicke_langsmith_tracing import wernicke_ls_traceable


class ProcessToolState(BaseGraphState):
    """
    State for the process tool node.

    Attributes:
        tool_call_id (str): The tool call ID.
        summary (str): Task summary.
    """

    tool_call_id: str
    summary: str


class ProcessToolNode(INode):
    """
    Node that executes the process tool logic and completes the task.
    """

    name = "ProcessToolNode"

    @wernicke_ls_traceable
    async def execute(self, graph_state: ProcessToolState) -> Dict[str, Any]:
        """
        Execute the process tool logic.

        Args:
            graph_state (ProcessToolState): The current state.

        Returns:
            Dict[str, Any]: Updated state with tool results and final output.
        """
        content = f"✅ Task completed successfully!\n\nSummary: {graph_state.summary}"

        tool_message = ToolMessage(
            content=content,
            tool_call_id=graph_state.tool_call_id,
            artifact={"status": "completed", "summary": graph_state.summary},
        )

        return {
            "tool_results": [tool_message],
            "final_output": content,
        }

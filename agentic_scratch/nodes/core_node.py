"""
==============================================================================
Name: core_node
Author: AI Assistant
Date: 10/20/2025
Description: Core agentic loop node for the agentic scratch orchestrator.
==============================================================================
"""

# Local imports
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from langchain_core.callbacks import BaseCallbackHandler

from wernicke.engines.llm.llm_callers.callers import LLMCallerAgent
from wernicke.engines.llm.llm_callers.config import UserSessionInfo
from wernicke.engines.llm.llm_callers.models import ActionType, ResponseMode
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.node_types.base import INode
from wernicke.shared.decorators.wernicke_langsmith_tracing import wernicke_ls_traceable

sys.path.insert(0, str(Path(__file__).parent.parent))
from callers.agentic_scratch_caller import AgenticScratchCallerConfig
from state import AgenticScratchState
from tools.process_tool import ProcessTool
from tools.search_tool import SearchTool


class CoreNode(INode):
    """
    Core node that implements the agentic loop.
    """

    name = "CoreNode"

    def __init__(
        self,
        user_session_info: UserSessionInfo,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
        http_async_client: Optional[httpx.AsyncClient] = None,
    ):
        """
        Initialize the node.

        Args:
            user_session_info (UserSessionInfo): User session information.
            callbacks (Optional[List[BaseCallbackHandler]]): Callbacks for tracking.
            http_async_client (Optional[httpx.AsyncClient]): HTTP client for API calls.
        """
        self._user_session_info = user_session_info
        self._callbacks = callbacks
        self._http_async_client = http_async_client

    @wernicke_ls_traceable
    async def execute(self, graph_state: AgenticScratchState) -> Dict[str, Any]:
        """
        Execute the core agentic loop.

        Args:
            graph_state (AgenticScratchState): The current state.

        Returns:
            Dict[str, Any]: Updated state with tool calls or completion.
        """
        if not graph_state.conversation:
            raise ValueError("Conversation is required to execute the CoreNode")

        # Check exit condition: if ProcessTool was called and we have results, exit
        if graph_state.tool_calls and graph_state.tool_calls[0].content.name == ProcessTool.name and graph_state.tool_results:
            return {"tool_calls": []}

        conversation = graph_state.conversation

        # Add tool results to conversation if we just ran tools
        if graph_state.tool_results:
            conversation = conversation.add_messages(graph_state.tool_results)

        # Set up LLM with tools
        llm_caller = LLMCallerAgent(
            caller_config=AgenticScratchCallerConfig,
            user_session_info=self._user_session_info,
            stream=False,
            tools=[
                SearchTool(),
                ProcessTool(),
            ],
            response_mode=ResponseMode.TOOL,
            http_async_client=self._http_async_client,
        )

        # Call the LLM
        resp, actions = await llm_caller.arun(inputs=conversation.get_conversation_context())

        # Add AI message to conversation
        updated_conversation = conversation.add_messages([resp])

        # Print out any reasoning summaries
        reasoning_messages = [action for action in actions if action.action_type == ActionType.REASONING]
        for summary in reasoning_messages:
            summary_string = "\n".join(summary.content)
            print(f"\n💭 REASONING:\n{summary_string}\n")

        # Extract tool calls
        tool_calls = [action for action in actions if action.action_type == ActionType.TOOL_CALL]

        if tool_calls:
            # Go run tools
            return {
                "conversation": updated_conversation,
                "tool_calls": tool_calls,
                "tool_results": {"kind": "rewrite", "value": []},
            }

        # No tool calls - shouldn't happen in TOOL mode, but handle gracefully
        return {
            "conversation": updated_conversation,
            "tool_calls": [],
            "tool_results": {"kind": "rewrite", "value": []},
        }

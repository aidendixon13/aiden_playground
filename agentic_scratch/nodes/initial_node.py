"""
==============================================================================
Name: initial_node
Author: AI Assistant
Date: 10/20/2025
Description: Initial node for the agentic scratch orchestrator.
==============================================================================
"""

# Local imports
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import BaseCallbackHandler

from wernicke.engines.llm.llm_callers.config import UserSessionInfo
from wernicke.engines.llm.llm_callers.factory import conversation_factory
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.node_types.base import INode
from wernicke.shared.decorators.wernicke_langsmith_tracing import wernicke_ls_traceable

sys.path.insert(0, str(Path(__file__).parent.parent))
from callers.agentic_scratch_caller import AgenticScratchCallerConfig
from state import AgenticScratchState


class InitialNode(INode):
    """
    Initial node that sets up the conversation.
    """

    name = "InitialNode"

    def __init__(
        self,
        user_session_info: UserSessionInfo,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
    ):
        """
        Initialize the node.

        Args:
            user_session_info (UserSessionInfo): User session information.
            callbacks (Optional[List[BaseCallbackHandler]]): Callbacks for tracking.
        """
        self._user_session_info = user_session_info
        self._callbacks = callbacks

    @wernicke_ls_traceable
    async def execute(self, graph_state: AgenticScratchState) -> Dict[str, Any]:
        """
        Initialize the conversation.

        Args:
            graph_state (AgenticScratchState): The current state.

        Returns:
            Dict[str, Any]: Updated state with conversation.
        """
        conversation = conversation_factory(
            caller_config=AgenticScratchCallerConfig,
            user_input=graph_state.user_input,
        )

        return {"conversation": conversation}

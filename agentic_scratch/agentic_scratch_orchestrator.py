"""
==============================================================================
Name: agentic_scratch_orchestrator
Author: AI Assistant
Date: 10/20/2025
Description: Test orchestrator for agentic tool-calling behavior.
==============================================================================
"""

from typing import List, Optional

import httpx

# Local imports
from factory import tool_call_node_factory, tool_call_state_model_factory
from langchain_core.callbacks import BaseCallbackHandler
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph.types import Send
from nodes.core_node import CoreNode
from nodes.initial_node import InitialNode
from packaging.version import Version
from state import AgenticScratchState
from tools.process_tool_node import ProcessToolNode
from tools.search_tool_node import SearchToolNode

from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.base import IGraphOrchestrator
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.node_types.basic_nodes import EndNode, PlaceHolderNode, StartNode
from wernicke.internals.session.user_session import UserSessionInfo


class AgenticScratchOrchestrator(IGraphOrchestrator):
    """
    Test orchestrator for agentic tool-calling behavior.
    """

    version = Version("1.0.0")
    description = "A graph orchestrator for testing agentic tool-calling patterns."

    graph_state = AgenticScratchState

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver,
        user_session_info: UserSessionInfo,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
        error_handling_active: bool = False,
        http_async_client: Optional[httpx.AsyncClient] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            checkpointer (BaseCheckpointSaver): The checkpointer for the graph.
            user_session_info (UserSessionInfo): User session information.
            callbacks (Optional[List[BaseCallbackHandler]]): Callbacks for tracking.
            error_handling_active (bool): Whether error handling is active.
            http_async_client (Optional[httpx.AsyncClient]): HTTP client for API calls.
        """
        self._user_session_info = user_session_info
        self._callbacks = callbacks
        self._http_async_client = http_async_client
        super().__init__(checkpointer=checkpointer, error_handling_active=error_handling_active)

    def compile_graph(self, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
        """
        Build and compile the LangGraph graph.

        Args:
            checkpointer (BaseCheckpointSaver): The checkpointer to use for the graph.

        Returns:
            CompiledStateGraph: The compiled graph.
        """
        # Initialize nodes
        initial_node = InitialNode(user_session_info=self._user_session_info, callbacks=self._callbacks)
        core_node = CoreNode(
            user_session_info=self._user_session_info,
            callbacks=self._callbacks,
            http_async_client=self._http_async_client,
        )
        place_holder_node = PlaceHolderNode()
        search_tool_node = SearchToolNode()
        process_tool_node = ProcessToolNode()

        # Build the graph
        graph = StateGraph(state_schema=self.graph_state)

        # Add nodes
        self.add_node(graph=graph, node=initial_node)
        self.add_node(graph=graph, node=core_node)
        self.add_node(graph=graph, node=place_holder_node)
        self.add_node(graph=graph, node=search_tool_node)
        self.add_node(graph=graph, node=process_tool_node)

        # Add edges
        self.add_edge(graph=graph, start_node=StartNode(), end_node=initial_node)
        self.add_edge(graph=graph, start_node=initial_node, end_node=core_node)

        # Conditional: continue to tools or end
        self.add_conditional_edge(
            graph=graph,
            start_node=core_node,
            conditional=self._finish_agent_conditional,
            conditional_node_map={
                PlaceHolderNode.name: place_holder_node,
                EndNode.name: EndNode(),
            },
        )

        # Conditional: route to correct tool (with parallel support)
        self.add_conditional_edge(
            graph=graph,
            start_node=place_holder_node,
            conditional=self._send_tools_conditional,
            conditional_node_map={
                SearchToolNode.name: search_tool_node,
                ProcessToolNode.name: process_tool_node,
            },
            is_parallel=True,
        )

        # Tools return to core node
        self.add_edge(
            graph=graph,
            start_node=[search_tool_node, process_tool_node],
            end_node=core_node,
        )

        return graph.compile(checkpointer=checkpointer)

    @staticmethod
    def _send_tools_conditional(graph_state: AgenticScratchState) -> List[Send]:
        """
        Dynamically route tool calls to the correct nodes.

        Args:
            graph_state (AgenticScratchState): The current state.

        Returns:
            List[Send]: List of Send objects for parallel tool execution.

        Raises:
            ValueError: If no tool calls are found.
        """
        if not graph_state.tool_calls:
            raise ValueError("No tool calls found in the graph state")

        tool_sends = []

        for tool_call_action in graph_state.tool_calls:
            tool_call_node = tool_call_node_factory(tool_name=tool_call_action.content.name)
            tool_call_state = tool_call_state_model_factory(tool_action=tool_call_action)

            tool_sends.append(Send(node=str(tool_call_node.name), arg=tool_call_state))

        return tool_sends

    @staticmethod
    def _finish_agent_conditional(graph_state: AgenticScratchState) -> str:
        """
        Determine if we should exit the agent or continue with tool calls.

        Args:
            graph_state (AgenticScratchState): The current state.

        Returns:
            str: The name of the next node to go to.
        """
        if graph_state.tool_calls:
            return PlaceHolderNode.name
        else:
            return EndNode.name

"""
==============================================================================
Name: factory
Author: AI Assistant
Date: 10/20/2025
Description: Factory for creating tool nodes and states.
==============================================================================
"""

from typing import Callable, Dict, Type

from pydantic import BaseModel

# Local imports
from tools.process_tool import ProcessTool
from tools.process_tool_node import ProcessToolNode, ProcessToolState
from tools.search_tool import SearchTool
from tools.search_tool_node import SearchToolNode, SearchToolState

from wernicke.engines.llm.llm_callers.models import ToolCallAction
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.node_types.base import INode


def tool_call_node_factory(tool_name: str) -> Type[INode]:
    """
    Factory for creating the node class from the tool name.

    Args:
        tool_name (str): Name of the tool.

    Returns:
        Type[INode]: The node class for the tool.

    Raises:
        NotImplementedError: If the tool name is not supported.
    """
    tool_nodes: Dict[str, Type[INode]] = {
        SearchTool.name: SearchToolNode,
        ProcessTool.name: ProcessToolNode,
    }

    if tool_name not in tool_nodes:
        raise NotImplementedError(f"Tool node factory does not support tool: {tool_name}")

    return tool_nodes[tool_name]


def tool_call_state_model_factory(tool_action: ToolCallAction, **kwargs) -> BaseModel:
    """
    Factory for creating the state model from the tool action.

    Args:
        tool_action (ToolCallAction): The tool call action.
        **kwargs: Additional keyword arguments.

    Returns:
        BaseModel: The state model for the tool.

    Raises:
        NotImplementedError: If the tool name is not supported.
    """
    tool_states: Dict[str, Callable] = {
        SearchTool.name: lambda tool_action, **kwargs: SearchToolState(
            tool_call_id=tool_action.id,
            query=tool_action.content.inputs.query,
        ),
        ProcessTool.name: lambda tool_action, **kwargs: ProcessToolState(
            tool_call_id=tool_action.id,
            summary=tool_action.content.inputs.summary,
        ),
    }

    if tool_action.content.name not in tool_states:
        raise NotImplementedError(f"Tool state model factory does not support tool: {tool_action.content.name}")

    constructor = tool_states[tool_action.content.name]
    return constructor(tool_action=tool_action, **kwargs)

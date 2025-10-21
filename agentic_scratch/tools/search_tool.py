"""
==============================================================================
Name: search_tool
Author: AI Assistant
Date: 10/20/2025
Description: Simple search tool for testing.
==============================================================================
"""

from typing import List, Literal, Optional, Type

from langchain_core.callbacks import AsyncCallbackHandler, BaseCallbackHandler
from pydantic import Field

from wernicke.engines.llm.auxillary.tools.wernicke_tools.base import ITool, IToolInputs


class SearchToolInputs(IToolInputs):
    """
    Input model for the Search tool.

    Attributes:
        query (str): The search query.
    """

    query: str = Field(description="The search query to execute.")


class SearchTool(ITool):
    """
    Simple search tool for testing agentic behavior.
    """

    name: Literal["SearchTool"] = "SearchTool"
    description: Literal["Search for information based on a query. Returns relevant results."] = (
        "Search for information based on a query. Returns relevant results."
    )

    @property
    def input_model(self) -> Type[SearchToolInputs]:
        """
        Returns the input model for the SearchTool.

        Returns:
            Type[SearchToolInputs]: The input model class.
        """
        return SearchToolInputs

    def _run(self, tool_inputs: SearchToolInputs, callbacks: Optional[List[BaseCallbackHandler]] = None, **kwargs) -> str:
        """
        This method is not implemented because this tool is used in a graph orchestrator.

        Args:
            tool_inputs (SearchToolInputs): The inputs to the tool.
            callbacks (Optional[List[BaseCallbackHandler]]): The list of callbacks.

        Raises:
            NotImplementedError: SearchTool does not support a run method.
        """
        raise NotImplementedError("SearchTool does not support a run method")

    async def _arun(self, tool_inputs: SearchToolInputs, callbacks: Optional[List[AsyncCallbackHandler]] = None, **kwargs) -> str:
        """
        This method is not implemented because this tool is used in a graph orchestrator.

        Args:
            tool_inputs (SearchToolInputs): The inputs to the tool.
            callbacks (Optional[List[AsyncCallbackHandler]]): The list of callbacks.

        Raises:
            NotImplementedError: SearchTool does not support an async run method.
        """
        raise NotImplementedError("SearchTool does not support an async run method")

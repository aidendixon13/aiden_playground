"""
==============================================================================
Name: process_tool
Author: AI Assistant
Date: 10/20/2025
Description: Process tool that finishes the task.
==============================================================================
"""

from typing import List, Literal, Optional, Type

from langchain_core.callbacks import AsyncCallbackHandler, BaseCallbackHandler
from pydantic import Field

from wernicke.engines.llm.auxillary.tools.wernicke_tools.base import ITool, IToolInputs


class ProcessToolInputs(IToolInputs):
    """
    Input model for the Process tool.

    Attributes:
        summary (str): Summary of what was accomplished.
    """

    summary: str = Field(description="Summary of the task completion and findings.")


class ProcessTool(ITool):
    """
    Tool that processes information and signals task completion.
    """

    name: Literal["ProcessTool"] = "ProcessTool"
    description: Literal["Process the gathered information and complete the task. Call this when you have all the information needed."] = (
        "Process the gathered information and complete the task. Call this when you have all the information needed."
    )

    @property
    def input_model(self) -> Type[ProcessToolInputs]:
        """
        Returns the input model for the ProcessTool.

        Returns:
            Type[ProcessToolInputs]: The input model class.
        """
        return ProcessToolInputs

    def _run(self, tool_inputs: ProcessToolInputs, callbacks: Optional[List[BaseCallbackHandler]] = None, **kwargs) -> str:
        """
        This method is not implemented because this tool is used in a graph orchestrator.

        Args:
            tool_inputs (ProcessToolInputs): The inputs to the tool.
            callbacks (Optional[List[BaseCallbackHandler]]): The list of callbacks.

        Raises:
            NotImplementedError: ProcessTool does not support a run method.
        """
        raise NotImplementedError("ProcessTool does not support a run method")

    async def _arun(self, tool_inputs: ProcessToolInputs, callbacks: Optional[List[AsyncCallbackHandler]] = None, **kwargs) -> str:
        """
        This method is not implemented because this tool is used in a graph orchestrator.

        Args:
            tool_inputs (ProcessToolInputs): The inputs to the tool.
            callbacks (Optional[List[AsyncCallbackHandler]]): The list of callbacks.

        Raises:
            NotImplementedError: ProcessTool does not support an async run method.
        """
        raise NotImplementedError("ProcessTool does not support an async run method")

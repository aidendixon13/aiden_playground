"""
==============================================================================
Name: agentic_scratch_caller
Author: AI Assistant
Date: 10/20/2025
Description: Caller configuration for the agentic scratch orchestrator.
==============================================================================
"""

from packaging.version import Version

from wernicke.engines.llm.llm_callers.factory import LLMTypeFactory
from wernicke.engines.llm.llm_callers.models import CallerChatConfig, MessageRole, OpenAIModels, PromptModel, WernickeModelProvider

AgenticScratchCallerConfig = CallerChatConfig(
    name="AgenticScratchCaller",
    version=Version("1.0.0"),
    description="Calls the Agentic Scratch caller to test agentic tool-calling behavior.",
    user_friendly_description="",
    llm_type=LLMTypeFactory.get_llm_type(model_provider=WernickeModelProvider.OPENAI),
    llm_init_kwargs={"model_name": OpenAIModels.GPT5, "reasoning": {"effort": "low", "summary": "auto"}, "include": ["reasoning.encrypted_content"]},
    prompt_messages=[
        PromptModel(
            role=MessageRole.SYSTEM,
            prompt=(
                """
# Role and Objective
You are an AI assistant that helps users accomplish tasks by using available tools.

# Instructions
- Use the available tools to gather information and complete the user's request.
- Think step by step about what information you need.
- Call tools when you need to search for information or process results.

## Available Tools

**SearchTool:**
- Use this tool to search for information.
- Input: search query
- Output: list of search results

**ProcessTool:**
- Call this tool when you have gathered all necessary information and are ready to complete the task.
- Input: a summary of what was accomplished
- This tool signals task completion.

## Process
1. Understand the user's request
2. Use SearchTool to gather any needed information (you may call it multiple times)
3. When you have sufficient information, call ProcessTool with a summary
4. The task ends after ProcessTool is called successfully

## Guidelines
- Be thorough in gathering information before calling ProcessTool
- Provide clear, helpful summaries
- You can call SearchTool multiple times if needed
- Always call ProcessTool to complete the task
"""
            ),
        ),
        PromptModel(
            role=MessageRole.USER,
            prompt="<user_request>{user_input}</user_request>",
        ),
    ],
)

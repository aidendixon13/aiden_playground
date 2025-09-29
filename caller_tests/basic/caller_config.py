"""
==============================================================================
Name: caller_config
Author: Aiden Playground
Date: 09/09/2025
Description:
Basic chat caller configuration for quick scratch experiments in the Aiden playground.

This defines a minimal `CallerChatConfig` that pairs a simple system prompt with a
user input prompt. It uses the OpenAI chat model configured via the project's
standard factory and environment configuration.

Usage:
- Import `AidenPlaygroundChatConfig` into a runner script and instantiate an
  `LLMCallerChat` with a `UserSessionInfo`.
==============================================================================
"""

from packaging.version import Version

from wernicke.engines.llm.llm_callers.factory import LLMTypeFactory
from wernicke.engines.llm.llm_callers.models import CallerChatConfig, MessageRole, OpenAIModels, PromptModel, WernickeModelProvider
from wernicke.engines.llm.llm_callers.prompt_constants import BASE_CORE_CHAT_PROMPT, OS_CHAT_SYSTEM_PREFIX

AidenPlaygroundChatConfig: CallerChatConfig = CallerChatConfig(
    name="AidenPlaygroundBasicChat",
    version=Version("1.0.0"),
    description="Basic chat caller used for quick experiments in Aiden's playground.",
    user_friendly_description="Simple chat caller: minimal prompts, easy to run and iterate.",
    llm_type=LLMTypeFactory.get_llm_type(model_provider=WernickeModelProvider.OPENAI),
    llm_init_kwargs={
        "model_name": OpenAIModels.GPT4_OMNI,
        "temperature": 0,
    },
    prompt_messages=[
        # Provide a concise, helpful system message using the shared core prompt
        PromptModel(
            role=MessageRole.SYSTEM,
            prompt="You are a helpful assistant that answers questions and makes calls to tools. If it is possible to parallelize tool calls, please do so.",
        ),
        # Single-turn user prompt that accepts an `input` field
        PromptModel(
            role=MessageRole.USER,
            prompt="{input}",
        ),
    ],
)

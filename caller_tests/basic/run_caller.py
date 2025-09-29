"""
==============================================================================
Name: run_caller
Author: Aiden Playground
Date: 09/09/2025
Description:
Scratch runner to instantiate the Aiden playground caller config and print the
result to stdout.

How to run:
    python experimentation/aiden_playground/run_caller.py
==============================================================================
"""

import asyncio
import os
import sys

from wernicke.engines.llm.llm_callers.callers import LLMCallerChat
from wernicke.internals.session.user_session import UserSessionInfo
from wernicke.tests.shared_utils.test_session import create_test_user_session


def _import_caller_config():
    """
    Import the playground caller config from the local folder.

    Returns:
        CallerChatConfig: The playground caller configuration object.
    """

    # Ensure this script can import sibling module `caller_config` when run directly
    current_dir = os.path.dirname(__file__)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    from caller_config import AidenPlaygroundChatConfig  # type: ignore

    return AidenPlaygroundChatConfig


async def main() -> None:
    """
    Create a local user session, run the playground caller once, and print output.

    Raises:
        Exception: Propagates exceptions for visibility when running locally.
    """

    user_session_info = create_test_user_session()

    # Load the caller config lazily to avoid import path issues until runtime
    caller_config = _import_caller_config()

    caller = LLMCallerChat(
        caller_config=caller_config,
        user_session_info=user_session_info,
    )

    # Build inputs using the auto-generated pydantic model from the caller
    inputs = caller.input_model(input="Say hello and tell me today's date in one sentence.")

    # Run asynchronously and print the final string output
    count = 10
    responses = {}

    for _ in range(count):
        result = await caller.arun(inputs=inputs)
        responses[result] = responses.get(result, 0) + 1

    dominant_response = 0
    for response, count in responses.items():
        print(f"{response}: {count}")
        if count > dominant_response:
            dominant_response = response
            dominant_response_count = response

    print(f"Responses diversity: {len(responses)}")
    print(f"Dominant response: {dominant_response}")
    print(f"Dominant response count: {dominant_response_count}")


if __name__ == "__main__":
    asyncio.run(main())

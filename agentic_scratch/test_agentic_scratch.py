"""
==============================================================================
Name: test_agentic_scratch
Author: AI Assistant
Date: 10/20/2025
Description: Test file for the agentic scratch orchestrator.
==============================================================================
"""

import asyncio
import sys
from pathlib import Path

import httpx
from langsmith import trace, tracing_context

# Add the source directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "source"))

# Local imports
from agentic_scratch_orchestrator import AgenticScratchOrchestrator
from state import AgenticScratchState

from wernicke.config.env_config.constants import EnvVar
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.graph_checkpointers.table_storage_checkpointer import (
    AzureTableStorageCheckpointer,
)
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.models import GraphInputModel, guid_to_str
from wernicke.engines.llm.models import guid
from wernicke.internals.session.user_session import CosmosDatabaseManager
from wernicke.shared.guid import new_guid
from wernicke.tests.shared_utils.test_session import create_test_user_session


async def run_agentic_scratch_orchestrator():
    """
    Test the agentic scratch orchestrator with a sample query.
    """
    user_session_info = create_test_user_session()

    async with CosmosDatabaseManager(user_session_info=user_session_info) as database_connection:
        user_session_info.database_connection = database_connection

        table_storage_checkpointer = AzureTableStorageCheckpointer(
            user_session_info=user_session_info,
        )

        orchestrator = AgenticScratchOrchestrator(
            checkpointer=table_storage_checkpointer,
            user_session_info=user_session_info,
            callbacks=[],
            http_async_client=httpx.AsyncClient(
                http2=True,
                limits=httpx.Limits(max_connections=200, max_keepalive_connections=20),
                follow_redirects=True,
            ),
        )

        graph_state = AgenticScratchState(
            user_input="Search for information about Python programming and then summarize what you found",
        )

        graph_inputs = GraphInputModel(
            graph_state=graph_state,
            thread_id=str(guid_to_str(new_guid())),
        )

        print("Starting Agentic Scratch Orchestrator...")
        print(f"User Input: {graph_state.user_input}")
        print("-" * 80)

        # Create trace_id for LangSmith tracing
        trace_id = guid.new_guid()

        # Enable tracing if configured
        tracing_enabled = user_session_info.environment_config_adapter.getenv(EnvVar.LS_TRACING) == "true"

        with tracing_context(enabled=tracing_enabled):
            # Open the inner context for the trace which adds more configurability
            with trace(
                name=f"AgenticScratchOrchestrator-{trace_id}",
                project_name=f"{user_session_info.environment_config_adapter.getenv(EnvVar.LANGCHAIN_PROJECT)}",
                run_id=trace_id,
                inputs=graph_state.model_dump(serialize_as_any=True),
                tags=[AgenticScratchOrchestrator.__name__, "test", "agentic_scratch"],
                metadata={"trace_id": trace_id, "test_run": True},
            ):
                # Run the orchestrator
                result, response_type = await orchestrator.arun(inputs=graph_inputs)

        print("\n" + "=" * 80)
        print("ORCHESTRATOR OUTPUT")
        print("=" * 80)

        print(f"\nResponse Type: {response_type}")
        print(f"\nTool Calls Made: {len(result.graph_state.tool_calls)}")

        if tracing_enabled:
            print(f"\n🔍 LangSmith Trace ID: {trace_id}")
            print(f"   Project: {user_session_info.environment_config_adapter.getenv(EnvVar.LANGCHAIN_PROJECT)}")

        if result.graph_state.tool_results:
            print(f"\nTool Results ({len(result.graph_state.tool_results)} total):")
            for i, tool_result in enumerate(result.graph_state.tool_results, 1):
                print(f"\n--- Tool Result {i} ---")
                print(tool_result.content)

        if result.graph_state.final_output:
            print(f"\n" + "=" * 80)
            print("FINAL OUTPUT")
            print("=" * 80)
            print(result.graph_state.final_output)


if __name__ == "__main__":
    asyncio.run(run_agentic_scratch_orchestrator())

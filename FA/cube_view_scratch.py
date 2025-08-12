import asyncio
import json
import os
import random
import time
from unittest.mock import patch

import httpx
from huggingface_hub import User
from pydantic import BaseModel

from wernicke.agents.rubix.cube_view.cube_view_orchestrator.cube_view_orchestrator import (
    CubeViewOrchestrator,
)
from wernicke.agents.rubix.cube_view.cube_view_orchestrator.state import (
    CubeViewOrchestratorState,
)
from wernicke.agents.rubix.cube_view.models import TimeScope
from wernicke.agents.rubix.cube_view.subgraph_orchestrators.cube_identifier_orchestrator.models import (
    SmartCubeIdentificationSettings,
)
from wernicke.app.dependencies import get_http_client
from wernicke.engines.llm.auxillary.artifacts.adapters.uow.cosmos import (
    ArtifactCosmosUnitOfWork,
)
from wernicke.engines.llm.auxillary.callbacks.streaming_callback import (
    AsyncStreamingCallbackHandler,
)
from wernicke.engines.llm.hil_adapter.base import HilInputFormat
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.graph_checkpointers.cosmos_db_checkpointer import (
    AzureCosmosDBCheckpointer,
)
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.graph_checkpointers.table_storage_checkpointer import (
    AzureTableStorageCheckpointer,
)
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.models import (
    GraphInputModel,
    GraphOutputModel,
    HilResponseModel,
)
from wernicke.engines.llm.models import ResponseType
from wernicke.engines.processing.onestream_metadata.dim_member_groupings.adapters.uow.cosmos import (
    DimMemberGroupingCosmosUnitOfWork,
)
from wernicke.engines.processing.settings.adapters.uow.company_settings.cosmos import (
    CompanySettingsCosmosUnitOfWork,
)
from wernicke.engines.processing.settings.adapters.uow.persona_settings.cosmos import (
    PersonaSettingsCosmosUnitOfWork,
)
from wernicke.engines.processing.settings.adapters.uow.ud_types_setting.cosmos import (
    UDSettingsCosmosUnitOfWork,
)
from wernicke.engines.processing.settings.adapters.uow.user_settings.cosmos import (
    UserSettingsCosmosUnitOfWork,
)
from wernicke.engines.retrieval.index_management.models import IndexService
from wernicke.internals.session import user_session
from wernicke.internals.session.user_session import UserSessionInfo
from wernicke.managers.cosmos_database.azure_cosmos_manager import CosmosDatabaseManager
from wernicke.shared.guid import guid_to_str
from wernicke.tests.evaluations.emulators.orchestrators.emulator import (
    OrchestratorEmulator,
)
from wernicke.tests.evaluations.emulators.orchestrators.models import (
    OrchestratorEmulatorInputModel,
    OrchestratorEmulatorOutputModel,
)
from wernicke.tests.mocks.onestream_metadata.expansion_count.expansion_count import (
    MockExpansionCountService,
)
from wernicke.tests.shared_utils.test_jwt import decode_test_jwt
from wernicke.tests.shared_utils.test_session import create_test_user_session


class InputModel(BaseModel):
    question: str
    cube_selection_instructions: str


questions = [
    # "Show me the revenue for `All_Cost_Centers` over the last year.",
    InputModel(
        question="For March 2025 show me the variance in my revenue accounts between actuals and budget for my strategic customers.",
        cube_selection_instructions="""
        If you are asked to select a cube, select the `Equipment Division` cube. If you are asked to select a dimension, select the `Revenue` dimension.
        If you are asked for a budget version, select the `BudgetFinal` version.
        If you are asked for a scenario, select the `Actual` scenario.
        If you are asked for a revenue view, select the `40000 (Tree)` view.
        If you are asked about cost centers, select the `CST1100` with our without a (Tree).
        """,
    ),
    # InputModel(
    #     question="Show me the revenue for North America Equipment over the last year.",
    #     cube_selection_instructions="If you are asked to select a cube, select the `Equipment Division` cube.",
    # ),
]


async def execute_orchestrator():
    print("🚀 Starting authentication process...")
    jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijk2MkNEN0ZEMzRDQzQ0ODBFNjA0NDNBNkY0NUEwNjVDIiwieDV0IjoiRTBJSkFhdlFTZWpEbDg2ZVo1T2ZQSmFSMW9JIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2xvY2FsaG9zdDo0NDM4NyIsIm5iZiI6MTc1MjI2MTY5MiwiaWF0IjoxNzUyMjYxNjkyLCJleHAiOjE3NTIyNjUyOTIsImF1ZCI6ImFwaTovL3dlcm5pY2tlIiwic2NvcGUiOlsib3BlbmlkIiwiZW1haWwiLCJwcm9maWxlIiwiZ3JvdXBzIiwiYXBpOi8vd2Vybmlja2Uvd2Vybmlja2UuYWxsIiwib2ZmbGluZV9hY2Nlc3MiXSwiYW1yIjpbInB3ZCJdLCJjbGllbnRfaWQiOiJzZW5zaWJsZWdlbmFpLnBob2VuaXgiLCJzdWIiOiI2ZjM3M2RlNC1jOWJmLTRlYzMtOGI2Ny01YzExZjIwYjViNWUiLCJhdXRoX3RpbWUiOjE3NTIyNjE2OTIsImlkcCI6ImxvY2FsIiwiZ3JvdXAiOlsiQWRtaW5pc3RyYXRvcnMiLCJFdmVyeW9uZSJdLCJleHRfaWF0IjpbIjE3NTIyNjE2OTIiLCIxNzUyMjYxNjkyIl0sInByZWZlcnJlZF91c2VybmFtZV9vaXMiOiJBZG1pbmlzdHJhdG9yIiwic2NoZW1lX29pcyI6InhmbmF0aXZlIiwic2lkIjoiQTQ4NkI3QjNBREQxMTEwODMzRjQ5MzkwRUM2MEQ3OEYiLCJqdGkiOiI2QzY3Q0JCMzE0QUM4NkFEMzRGNTYwMzFEN0Y2NjRFMCJ9.v3Teksl2HQEmFMSjQXyh-ndVbsu3vXbiifwlr_em2qXSGTp5pSCsO85HuYcgvOFyzs82nuSgdNW0MyleTnbgeigZG7pTYG9txEmtU7psjDJmKiZxJSZ8zHO0cdHwCIecV30scSHqCC3Avhd6uY4w65fkOgG7VdE8f1SQNL5pUitdKN6yEIxL0e3YbzXMtxrklM6jw8oghM73hRXBo6gVuuRgXgqciMwyYe36ojmZYNY386dJnnlNEPYt7qoNxRLFZtT7eOEZz9OprCWAIsOmCLEiOkw3gg1o8BTGnMTzzOjaPHQ-i_LZyWvf4EqWg8ye6mzN4aTcJT4BttiLOrW0Jw"

    # user_session_info = create_test_user_session(decoded_jwt=decode_test_jwt(encoded_jwt=jwt))
    user_session_info = create_test_user_session()

    print(f"🎯 Using token: {user_session_info.access_token[:50]}...")

    async with CosmosDatabaseManager(user_session_info=user_session_info) as database_connection:
        user_session_info.database_connection = database_connection

        table_storage_checkpointer = AzureTableStorageCheckpointer(
            user_session_info=user_session_info,
        )

        ud_settings_uow = UDSettingsCosmosUnitOfWork(user_session_info=user_session_info)

        # get the ud types
        with ud_settings_uow as ud_settings_uow:
            ud_types_settings_repo = ud_settings_uow.ud_settings_repo
            ud_types_settings = ud_types_settings_repo.get_ud_type_all()
            ud_types = {ud_type.name: guid_to_str(ud_type.id) for ud_type in ud_types_settings}

        handler = AsyncStreamingCallbackHandler()

        orchestrator = CubeViewOrchestrator(
            checkpointer=table_storage_checkpointer,
            user_session_info=user_session_info,
            index_service=IndexService.AZURE_COGNITIVE_SEARCH,
            error_handling_active=True,
            dim_member_grouping_uow=DimMemberGroupingCosmosUnitOfWork(user_session_info=user_session_info),
            user_settings_uow=UserSettingsCosmosUnitOfWork(user_session_info=user_session_info),
            personas_uow=PersonaSettingsCosmosUnitOfWork(user_session_info=user_session_info),
            company_settings_uow=CompanySettingsCosmosUnitOfWork(user_session_info=user_session_info),
            ud_types_settings_uow=ud_settings_uow,
            async_http_client=httpx.AsyncClient(),
            callbacks=[handler],
        )

        all_artifacts = []
        entry_counter = 0

        for input_model in questions:
            # Create entry directory
            eval_data_dir = f"experimentation/aiden_playground/FA/eval_data/entry_id_{entry_counter}"
            os.makedirs(eval_data_dir, exist_ok=True)

            # Prepare inputs data (only needs to be created once per question)
            graph_state = CubeViewOrchestratorState(
                user_input=input_model.question,
                ud_types=ud_types,
                cube_name="Equipment Division",
                time_scope=TimeScope.SYSTEM_TIME,
            )

            inputs_data = {
                "graph_state": graph_state.model_dump() if hasattr(graph_state, "model_dump") else str(graph_state),
                "orchestrator_config": {
                    "index_service": "AZURE_COGNITIVE_SEARCH",
                    "error_handling_active": True,
                    "max_iterations": 5,
                    "force_response": True,
                },
                "question": input_model.question,
                "cube_selection_instructions": input_model.cube_selection_instructions,
                "ud_types": ud_types,
            }

            # Save inputs.json (once per question)
            inputs_file = os.path.join(eval_data_dir, "inputs.json")
            with open(inputs_file, "w") as f:
                json.dump(inputs_data, f, indent=2, default=str)

            # Run the question 5 times and collect results
            results_list = []

            for i in range(5):
                thread_id = random.randint(1, 10000)

                graph_inputs = GraphInputModel(
                    graph_state=graph_state,
                    thread_id=str(thread_id),
                )

                # Create trace_id if tracing is enabled
                # trace_id = guid.new_guid() if user_session_info.environment_config_adapter.getenv(EnvVar.TRACING) == "true" else None
                # Open the tracing context if tracing is enabled. If it is not enabled, this context will not do anything.
                # results = []
                # with tracing_context(enabled=True if user_session_info.environment_config_adapter.getenv(EnvVar.TRACING) == "true" else False):
                #     # Open the inner context for the trace which adds more configurability to how the trace is logged
                #     with trace(
                #         name=f"CubeViewOrchestrator-{trace_id}",
                #         project_name=f"{user_session_info.environment_config_adapter.getenv(EnvVar.LANGCHAIN_PROJECT)}",
                #         run_id=trace_id,
                #         inputs=graph_state.model_dump(serialize_as_any=True),
                #         tags=[CubeViewOrchestrator.__name__],
                #         metadata={"trace_id": trace_id},
                #     ):
                start = time.time()
                try:
                    orchestrator_emulator_input_model = OrchestratorEmulatorInputModel(
                        orchestrator=orchestrator,
                        inputs=graph_inputs,
                        thread_id=str(thread_id),
                        user_notes=input_model.cube_selection_instructions,
                    )

                    orchestrator_emulator = OrchestratorEmulator(
                        user_session_info=user_session_info, max_iterations=5, http_async_client=httpx.AsyncClient(), force_response=True
                    )

                    # Patch ExpansionCountService with the mock
                    with patch(
                        "wernicke.agents.rubix.cube_view.subgraph_orchestrators.cube_view_builder_orchestrator.state.ExpansionCountService",
                        MockExpansionCountService,
                    ):
                        results: OrchestratorEmulatorOutputModel = await orchestrator_emulator.run(orchestrator_emulator_input_model)
                        print(results)

                    # Find CubeViewArtifact object in final_outputs list
                    artifact_id = None
                    artifact = None

                    if hasattr(results.graph_state, "final_outputs") and results.graph_state.final_outputs:
                        for output in results.graph_state.final_outputs:
                            # Check if this output is a CubeViewArtifact object (has id attribute and artifact_type)
                            if hasattr(output, "id") and hasattr(output, "artifact_type"):
                                artifact_id = output.id
                                break

                    if artifact_id:
                        artifact_uow = ArtifactCosmosUnitOfWork(user_session_info=user_session_info)
                        async with artifact_uow:
                            artifact_repo = artifact_uow.artifact_repo
                            artifact = await artifact_repo.get_artifact_async(artifact_id=artifact_id)

                        print(f"Entry {entry_counter}, Run {i+1}: Found artifact {artifact_id}")
                    else:
                        print(f"Entry {entry_counter}, Run {i+1}: No CubeViewArtifact found in final_outputs")

                    result_entry = {
                        "run_number": i + 1,
                        "thread_id": thread_id,
                        "artifact_id": artifact_id,
                        "artifact_data": (
                            artifact.model_dump() if artifact and hasattr(artifact, "model_dump") else str(artifact) if artifact else None
                        ),
                        "timestamp": time.time(),
                    }
                    results_list.append(result_entry)

                except NotImplementedError:
                    results = [None, None]
                    result_entry = {
                        "run_number": i + 1,
                        "thread_id": thread_id,
                        "error": "NotImplementedError",
                        "artifact_data": None,
                        "timestamp": time.time(),
                    }
                    results_list.append(result_entry)

                end = time.time()

                # print(f"Orchestrator time: {end - start:.2f}")

                # print(thread_id)
                thread_id += 1

            # Save results.json (5 runs per question)
            results_file = os.path.join(eval_data_dir, "results.json")
            with open(results_file, "w") as f:
                json.dump(results_list, f, indent=2, default=str)

            # Add to overall collection for summary
            all_artifacts.extend(results_list)
            entry_counter += 1

        print(f"\n✅ All entries saved to individual directories:")
        print(f"   - Each entry has inputs.json and results.json")
        print(f"   - Directory: experimentation/aiden_playground/FA/eval_data/entry_id_<N>/")
        print(f"📊 Successfully completed {entry_counter} question(s) with 5 runs each")

        # for thought in handler._queue.thoughts:
        #     print(json.loads(thought)["system_message"]["message"])

        return None, None


if __name__ == "__main__":
    import asyncio
    from unittest.mock import MagicMock, patch

    # Approach 1: Use our custom mock class
    with patch(
        "wernicke.agents.rubix.cube_view.subgraph_orchestrators.cube_view_builder_orchestrator.state.ExpansionCountService", MockExpansionCountService
    ):
        result, response_type = asyncio.run(execute_orchestrator())
        print(result)
        print(response_type)

    # Alternative approach 2: If above doesn't work, try this more explicit approach
    # with patch("wernicke.agents.rubix.cube_view.subgraph_orchestrators.cube_view_builder_orchestrator.state.ExpansionCountService") as mock_class:
    #     mock_instance = MagicMock()
    #     mock_instance.get_member_expansion_count.return_value = 5
    #     mock_class.return_value = mock_instance
    #
    #     result, response_type = asyncio.run(execute_orchestrator())
    #     print(result)
    #     print(response_type)
    # if response_type == ResponseType.HIL:
    #     for hil_response in result.hil_outputs:
    #         print(hil_response.hil_node_name)
    #         print(hil_response.hil_modality.modality_data.text)
    #         for modal in hil_response.hil_modality.modality_data.options:
    #             print(modal.label)

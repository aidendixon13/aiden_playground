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
    BaseGraphState,
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
from wernicke.tests.mocks.datetime_mock import MockDatetime
from wernicke.tests.mocks.onestream_metadata.expansion_count.expansion_count import (
    MockExpansionCountService,
)
from wernicke.tests.shared_utils.test_jwt import decode_test_jwt
from wernicke.tests.shared_utils.test_session import create_test_user_session


class InputModel(BaseModel):
    question: str
    eval_notes: str


# Set the current index for directory naming
CURRENT_INDEX = 12

# Single question with eval notes
question = InputModel(
    question="Show total marketing spend in North America from October to December 2024.",
    eval_notes="""
    If you are asked to select a cube, select the `Equipment Division` cube.
    """,
)


async def execute_orchestrator():
    print("🚀 Starting authentication process...")
    jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijk2MkNEN0ZEMzRDQzQ0ODBFNjA0NDNBNkY0NUEwNjVDIiwieDV0IjoiRTBJSkFhdlFTZWpEbDg2ZVo1T2ZQSmFSMW9JIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2xvY2FsaG9zdDo0NDM4NyIsIm5iZiI6MTc1NTA5NDIwMywiaWF0IjoxNzU1MDk0MjAzLCJleHAiOjE3NTUwOTc4MDMsImF1ZCI6ImFwaTovL3dlcm5pY2tlIiwic2NvcGUiOlsib3BlbmlkIiwiZW1haWwiLCJwcm9maWxlIiwiZ3JvdXBzIiwiYXBpOi8vd2Vybmlja2Uvd2Vybmlja2UuYWxsIiwib2ZmbGluZV9hY2Nlc3MiXSwiYW1yIjpbInB3ZCJdLCJjbGllbnRfaWQiOiJzZW5zaWJsZWdlbmFpLnBob2VuaXgiLCJzdWIiOiI2ZjM3M2RlNC1jOWJmLTRlYzMtOGI2Ny01YzExZjIwYjViNWUiLCJhdXRoX3RpbWUiOjE3NTUwOTQyMDMsImlkcCI6ImxvY2FsIiwiZ3JvdXAiOlsiQWRtaW5pc3RyYXRvcnMiLCJFdmVyeW9uZSJdLCJleHRfaWF0IjpbIjE3NTUwOTQyMDMiLCIxNzU1MDk0MjAzIl0sInByZWZlcnJlZF91c2VybmFtZV9vaXMiOiJBZG1pbmlzdHJhdG9yIiwic2NoZW1lX29pcyI6InhmbmF0aXZlIiwic2lkIjoiNUE2RURERkM2Njk5QzYxRDM2QzdBMjFCQTlERTFFN0UiLCJqdGkiOiI5MDU3MjhCMzQ4OTI4RkRBMzhFM0QwMUY1QjYxNTZDMyJ9.JWSsSkZzj7G9aGXINY7Ha3SOiYo43NDNI681qsQ73T2KtCJSH5McryXqfVBZ3DF05mUzlVcnOtDSa3I8pmgi2qNVBXfwQkJWduca8T1QMbJV__jjsbF7b3tuws7gGlD0nb0EqJOtb_W3TeiYjMd-d9xVo3t9lgH9vhr_dL_pK_N59kPqz5sJITRCwVhYmRYjUx1NrUtmjfj7zLkVym7hAx6E-eGh-_Dmihc3cvHD7-lacvMmjJjBKdbeujKy_XxplHlwlbYzFmAkLa4y-rPD0RNAUmfr_o36MfEF6qtLTicHB1RiAPmHFeyE6ZBrt2eFGKUnzlUPsWRXiYkSdDXIxg"

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

        # Create entry directory using the current index
        eval_data_dir = f"experimentation/aiden_playground/FA/eval_data/entry_id_{CURRENT_INDEX}"
        os.makedirs(eval_data_dir, exist_ok=True)

        # Prepare inputs data (only needs to be created once per question)
        graph_state = CubeViewOrchestratorState(
            user_input=question.question,
            ud_types=ud_types,
            time_scope=TimeScope.NONE,
        )

        inputs_data = {
            "graph_state": graph_state.model_dump() if hasattr(graph_state, "model_dump") else str(graph_state),
            "orchestrator_config": {
                "index_service": "AZURE_COGNITIVE_SEARCH",
                "error_handling_active": True,
                "max_iterations": 5,
                "force_response": True,
            },
            "question": question.question,
            "eval_notes": question.eval_notes,
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
                    obj=orchestrator,
                    graph_inputs=graph_inputs,
                    entry_inputs={},
                    thread_id=str(thread_id),
                    eval_notes=question.eval_notes,
                )

                orchestrator_emulator = OrchestratorEmulator(
                    user_session_info=user_session_info, max_iterations=5, http_async_client=httpx.AsyncClient(), force_response=False
                )

                # Patch both ExpansionCountService and datetime.now() with mocks
                with (
                    patch(
                        "wernicke.agents.rubix.cube_view.subgraph_orchestrators.cube_view_builder_orchestrator.state.ExpansionCountService",
                        MockExpansionCountService,
                    ),
                    patch("wernicke.agents.rubix.cube_view.helpers.datetime", MockDatetime),
                ):
                    results: OrchestratorEmulatorOutputModel = await orchestrator_emulator.run(orchestrator_emulator_input_model)
                    print(results)

                # Find CubeViewArtifact object in final_outputs list
                artifact_id = None
                artifact = None

                graph_outputs: BaseGraphState = results.outputs[0].graph_state

                if hasattr(graph_outputs, "final_outputs") and graph_outputs.final_outputs:
                    for output in graph_outputs.final_outputs:
                        # Check if this output is a CubeViewArtifact object (has id attribute and artifact_type)
                        if hasattr(output, "id") and hasattr(output, "artifact_type"):
                            artifact_id = output.id
                            break

                if artifact_id:
                    artifact_uow = ArtifactCosmosUnitOfWork(user_session_info=user_session_info)
                    async with artifact_uow:
                        artifact_repo = artifact_uow.artifact_repo
                        artifact = await artifact_repo.get_artifact_async(artifact_id=artifact_id)

                    print(f"Entry {CURRENT_INDEX}, Run {i+1}: Found artifact {artifact_id}")
                else:
                    print(f"Entry {CURRENT_INDEX}, Run {i+1}: No CubeViewArtifact found in final_outputs")

                # Only save the artifact_data wrapped in key
                artifact_data = artifact.model_dump() if artifact and hasattr(artifact, "model_dump") else str(artifact) if artifact else None
                results_list.append({"artifact_data": artifact_data})

            except NotImplementedError:
                results = [None, None]
                # Only save the artifact_data (None for errors) wrapped in key
                results_list.append({"artifact_data": None})

            end = time.time()

            # print(f"Orchestrator time: {end - start:.2f}")

            # print(thread_id)
            thread_id += 1

        # Deduplicate results based on artifact_data content
        unique_results = []
        seen_artifact_data = set()

        for result in results_list:
            if result is not None and result.get("artifact_data") is not None:
                # Get the nested artifact_data content for comparison
                artifact_data_content = result["artifact_data"].get("artifact_data")
                if artifact_data_content is not None:
                    # Convert to JSON string for comparison
                    content_str = json.dumps(artifact_data_content, sort_keys=True, default=str)
                    if content_str not in seen_artifact_data:
                        seen_artifact_data.add(content_str)
                        unique_results.append(result)
            elif result is None:
                # Keep None results (errors)
                unique_results.append(result)

        print(f"📊 Deduplication: {len(results_list)} total results → {len(unique_results)} unique results")

        # Save results.json with unique results only
        results_file = os.path.join(eval_data_dir, "results.json")
        with open(results_file, "w") as f:
            json.dump(unique_results, f, indent=2, default=str)

        # Add to overall collection for summary
        all_artifacts.extend(results_list)

        print(f"\n✅ Entry saved to directory:")
        print(f"   - Entry has inputs.json and results.json")
        print(f"   - Directory: experimentation/aiden_playground/FA/eval_data/entry_id_{CURRENT_INDEX}/")
        print(f"📊 Successfully completed 1 question with 5 runs")

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

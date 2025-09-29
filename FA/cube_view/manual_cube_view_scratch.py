import asyncio
import random
import time
from unittest.mock import patch

import httpx
from langsmith import trace, tracing_context
from pydantic import BaseModel

from wernicke.agents.rubix.cube_view.cube_view_orchestrator.cube_view_orchestrator import (
    CubeViewOrchestrator,
)
from wernicke.agents.rubix.cube_view.cube_view_orchestrator.state import (
    CubeViewOrchestratorState,
)
from wernicke.agents.rubix.cube_view.models import TimeScope
from wernicke.config.env_config.constants import EnvVar
from wernicke.engines.llm.auxillary.artifacts.adapters.uow.cosmos import (
    ArtifactCosmosUnitOfWork,
)
from wernicke.engines.llm.auxillary.callbacks.streaming_callback import (
    AsyncStreamingCallbackHandler,
)
from wernicke.engines.llm.hil_adapter.base import HilInputFormat
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.graph_checkpointers.table_storage_checkpointer import (
    AzureTableStorageCheckpointer,
)
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.models import (
    BaseGraphState,
    GraphInputModel,
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
from wernicke.managers.cosmos_database.azure_cosmos_manager import CosmosDatabaseManager
from wernicke.shared.guid import guid_to_str, new_guid, str_to_guid

# Removed unused emulator imports for direct orchestrator interaction
# from wernicke.tests.mocks.onestream_metadata.expansion_count.expansion_count import (
#     MockExpansionCountService,
# )
from wernicke.tests.shared_utils.test_session import create_test_user_session


class InputModel(BaseModel):
    question: str
    eval_notes: str


def handle_hil_interaction(hil_outputs):
    """
    Handle Human-in-Loop interactions by displaying HIL content and getting user input.

    Args:
        hil_outputs: List of HIL output models from the orchestrator

    Returns:
        List[HilResponseModel]: List of user responses to HIL prompts
    """
    hil_responses = []

    print("\n" + "=" * 80)
    print("🧑‍💻 HUMAN-IN-LOOP INTERACTION REQUIRED")
    print("=" * 80)

    for i, hil in enumerate(hil_outputs):
        print(f"\n📋 HIL Node #{i+1}: {hil.hil_node_name}")
        print(f"💬 Question: {hil.hil_modality.modality_data.text}")

        # Handle different input formats
        if hil.hil_modality.input_format == HilInputFormat.SINGLE_SELECT:
            print("\n📝 Available Options:")
            for j, option in enumerate(hil.hil_modality.modality_data.options):
                print(f"  {j+1}. {option.label}")

            while True:
                try:
                    choice = input(f"\n👆 Select an option (1-{len(hil.hil_modality.modality_data.options)}): ").strip()
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(hil.hil_modality.modality_data.options):
                        selected_option = hil.hil_modality.modality_data.options[choice_idx]
                        print(f"✅ Selected: {selected_option.label}")
                        hil_responses.append(
                            HilResponseModel(
                                hil_node_name=hil.hil_node_name, input_format=HilInputFormat.SINGLE_SELECT, response_value=selected_option.value
                            )
                        )
                        break
                    else:
                        print("❌ Invalid choice. Please try again.")
                except ValueError:
                    print("❌ Please enter a valid number.")

        elif hil.hil_modality.input_format == HilInputFormat.MULTI_SELECT:
            print("\n📝 Available Options (select multiple by entering comma-separated numbers):")
            for j, option in enumerate(hil.hil_modality.modality_data.options):
                print(f"  {j+1}. {option.label}")

            while True:
                try:
                    choices = input(f"\n👆 Select options (e.g., '1,3,5'): ").strip().split(",")
                    choice_indices = [int(c.strip()) - 1 for c in choices]

                    if all(0 <= idx < len(hil.hil_modality.modality_data.options) for idx in choice_indices):
                        selected_options = [hil.hil_modality.modality_data.options[idx] for idx in choice_indices]
                        selected_values = [opt.value for opt in selected_options]
                        selected_labels = [opt.label for opt in selected_options]

                        print(f"✅ Selected: {', '.join(selected_labels)}")
                        hil_responses.append(
                            HilResponseModel(
                                hil_node_name=hil.hil_node_name, input_format=HilInputFormat.MULTI_SELECT, response_value=selected_values
                            )
                        )
                        break
                    else:
                        print("❌ Invalid choices. Please try again.")
                except ValueError:
                    print("❌ Please enter valid numbers separated by commas.")

        elif hil.hil_modality.input_format == HilInputFormat.CUBE_SELECT:
            print("\n📝 Available Cubes:")
            for j, option in enumerate(hil.hil_modality.modality_data.options):
                print(f"  {j+1}. {option.label}")

            while True:
                try:
                    choice = input(f"\n👆 Select a cube (1-{len(hil.hil_modality.modality_data.options)}): ").strip()
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(hil.hil_modality.modality_data.options):
                        selected_option = hil.hil_modality.modality_data.options[choice_idx]
                        print(f"✅ Selected cube: {selected_option.label}")
                        hil_responses.append(
                            HilResponseModel(
                                hil_node_name=hil.hil_node_name, input_format=HilInputFormat.CUBE_SELECT, response_value=selected_option.value
                            )
                        )
                        break
                    else:
                        print("❌ Invalid choice. Please try again.")
                except ValueError:
                    print("❌ Please enter a valid number.")

        else:
            # For other input formats, allow free text input
            print(f"\n💬 Input format: {hil.hil_modality.input_format}")
            if hasattr(hil.hil_modality.modality_data, "options") and hil.hil_modality.modality_data.options:
                print("📝 Available Options:")
                for j, option in enumerate(hil.hil_modality.modality_data.options):
                    print(f"  - {option.label}")

            user_input = input("\n✍️  Enter your response: ").strip()
            print(f"✅ Your response: {user_input}")
            hil_responses.append(
                HilResponseModel(hil_node_name=hil.hil_node_name, input_format=hil.hil_modality.input_format, response_value=user_input)
            )

    print("\n" + "=" * 80)
    print("✅ HIL interaction completed!")
    print("=" * 80)

    return hil_responses


# Single question with eval notes
question = InputModel(
    question="show me the variance between actual and budgets for my reveune accounts for North America.",
    eval_notes="""
    If you are asked to select a cube, select the `Equipment Division` cube.
    If you are asked about what measure would you like to use to calculate the difference between Actual and BudgetFinal, you can use 40000.
    """,
)


async def execute_orchestrator():
    print("🚀 Starting authentication process...")

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

        # Prepare graph state
        graph_state = CubeViewOrchestratorState(
            user_input=question.question,
            ud_types=ud_types,
            time_scope=TimeScope.NONE,
            cube_name="Equipment Division",  # Assuming the user selects this cube
            # persona_id=str_to_guid("2f616574-e6d6-8042-0027-5d603322c3c5"),
        )

        thread_id = random.randint(1, 10000)

        graph_inputs = GraphInputModel(
            graph_state=graph_state,
            thread_id=str(thread_id),
        )

        # Create trace_id if tracing is enabled
        trace_id = new_guid() if user_session_info.environment_config_adapter.getenv(EnvVar.LS_TRACING) == "true" else None

        start = time.time()
        try:
            # Open the tracing context if tracing is enabled. If it is not enabled, this context will not do anything.
            with tracing_context(enabled=True if user_session_info.environment_config_adapter.getenv(EnvVar.LS_TRACING) == "true" else False):
                # Open the inner context for the trace which adds more configurability to how the trace is logged
                with trace(
                    name=f"CubeViewOrchestrator-{trace_id}",
                    project_name=f"{user_session_info.environment_config_adapter.getenv(EnvVar.LANGCHAIN_PROJECT)}",
                    run_id=trace_id,
                    inputs=graph_state.model_dump(serialize_as_any=True),
                    tags=[CubeViewOrchestrator.__name__],
                    metadata={"trace_id": trace_id},
                ):
                    # Instead of using the orchestrator emulator, run the orchestrator directly to handle HIL
                    max_iterations = 10
                    current_inputs = graph_inputs

                    for iteration in range(max_iterations):
                        print(f"\n🔄 Iteration {iteration + 1}/{max_iterations}")
                        print(f"📝 Current inputs: {current_inputs.graph_state.user_input}")

                        # Run the orchestrator
                        result, response_type = await orchestrator.arun(inputs=current_inputs)

                        print(f"📊 Response Type: {response_type}")

                        if response_type == ResponseType.HIL:
                            print("🔄 HIL response detected - intercepting for manual interaction")

                            # Handle HIL interaction manually
                            hil_responses = handle_hil_interaction(result.hil_outputs)

                            # Prepare inputs for next iteration with HIL responses
                            current_inputs = GraphInputModel(graph_state=result.graph_state, thread_id=str(thread_id), hil_responses=hil_responses)

                        elif response_type == ResponseType.FULL:
                            print("✅ Full response received - orchestrator completed!")
                            print(f"⏱️  Total execution time: {time.time() - start:.2f} seconds")
                            final_result = result
                            break
                        else:
                            print(f"❓ Unknown response type: {response_type}")
                            break
                    else:
                        print(f"⚠️  Reached maximum iterations ({max_iterations}) without full completion")
                        final_result = result

                    # Check for errors in final graph state
                    graph_outputs: BaseGraphState = final_result.graph_state
                    artifact_id = None
                    artifact = None

                    if hasattr(graph_outputs, "errors") and graph_outputs.errors:
                        print("❌ Errors found in graph state:")
                        for error_id, error_msg in graph_outputs.errors:
                            print(f"  - [{error_id}] {error_msg}")
                        # Skip artifact fetching if there are errors
                    else:
                        print("✅ No Errors!")

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

                            print(f"Found artifact {artifact_id}")
                        else:
                            print(f"No CubeViewArtifact found in final_outputs")

                    # Only save the artifact_data wrapped in key
                    artifact_data = artifact.model_dump() if artifact and hasattr(artifact, "model_dump") else str(artifact) if artifact else None
                    print({"artifact_data": artifact_data})
                    return final_result, response_type

        except NotImplementedError as e:
            print(f"❌ NotImplementedError: {e}")
            return None, None
        except Exception as e:
            print(f"❌ Error during execution: {e}")
            return None, None


if __name__ == "__main__":
    from unittest.mock import patch

    # Patch ExpansionCountService with our mock
    # with patch(
    #     "wernicke.agents.rubix.cube_view.subgraph_orchestrators.cube_view_builder_orchestrator.state.ExpansionCountService", MockExpansionCountService
    # ):
    result, response_type = asyncio.run(execute_orchestrator())
    print("\n📋 Final Results:")
    print(f"Result: {result}")
    print(f"Response Type: {response_type}")

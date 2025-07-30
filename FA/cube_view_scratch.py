import asyncio
import random
import time

import httpx
from huggingface_hub import User

from wernicke.agents.rubix.cube_view.cube_view_orchestrator.cube_view_orchestrator import CubeViewOrchestrator
from wernicke.agents.rubix.cube_view.cube_view_orchestrator.state import CubeViewOrchestratorState
from wernicke.agents.rubix.cube_view.models import TimeScope
from wernicke.agents.rubix.cube_view.subgraph_orchestrators.cube_identifier_orchestrator.models import SmartCubeIdentificationSettings
from wernicke.engines.llm.auxillary.callbacks.streaming_callback import AsyncStreamingCallbackHandler
from wernicke.engines.llm.hil_adapter.base import HilInputFormat
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.graph_checkpointers.cosmos_db_checkpointer import AzureCosmosDBCheckpointer
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.graph_checkpointers.table_storage_checkpointer import (
    AzureTableStorageCheckpointer,
)
from wernicke.engines.llm.llm_orchestrators.graph_llm_orchestrators.models import GraphInputModel, HilResponseModel
from wernicke.engines.llm.models import ResponseType
from wernicke.engines.processing.onestream_metadata.dim_member_groupings.adapters.uow.cosmos import DimMemberGroupingCosmosUnitOfWork
from wernicke.engines.processing.settings.adapters.uow.company_settings.cosmos import CompanySettingsCosmosUnitOfWork
from wernicke.engines.processing.settings.adapters.uow.persona_settings.cosmos import PersonaSettingsCosmosUnitOfWork
from wernicke.engines.processing.settings.adapters.uow.ud_types_setting.cosmos import UDSettingsCosmosUnitOfWork
from wernicke.engines.processing.settings.adapters.uow.user_settings.cosmos import UserSettingsCosmosUnitOfWork
from wernicke.engines.retrieval.index_management.models import IndexService
from wernicke.internals.session.user_session import UserSessionInfo
from wernicke.managers.cosmos_database.azure_cosmos_manager import CosmosDatabaseManager
from wernicke.shared.guid import guid_to_str

questions = [
    # "Show me the revenue for `All_Cost_Centers` over the last year.",
    # "Show me `Expense Breakdown(Dimension Member Grouping)` `Actual: Actual` vs `BudgetFinal: Budget Final` for our marketing cost center in April 2025",
    "Show me the revenue for North America Equipment over the last year.",
]


async def execute_orchestrator():
    print("🚀 Starting authentication process...")
    jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijk2MkNEN0ZEMzRDQzQ0ODBFNjA0NDNBNkY0NUEwNjVDIiwieDV0IjoiRTBJSkFhdlFTZWpEbDg2ZVo1T2ZQSmFSMW9JIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2xvY2FsaG9zdDo0NDM4NyIsIm5iZiI6MTc1MjI2MTY5MiwiaWF0IjoxNzUyMjYxNjkyLCJleHAiOjE3NTIyNjUyOTIsImF1ZCI6ImFwaTovL3dlcm5pY2tlIiwic2NvcGUiOlsib3BlbmlkIiwiZW1haWwiLCJwcm9maWxlIiwiZ3JvdXBzIiwiYXBpOi8vd2Vybmlja2Uvd2Vybmlja2UuYWxsIiwib2ZmbGluZV9hY2Nlc3MiXSwiYW1yIjpbInB3ZCJdLCJjbGllbnRfaWQiOiJzZW5zaWJsZWdlbmFpLnBob2VuaXgiLCJzdWIiOiI2ZjM3M2RlNC1jOWJmLTRlYzMtOGI2Ny01YzExZjIwYjViNWUiLCJhdXRoX3RpbWUiOjE3NTIyNjE2OTIsImlkcCI6ImxvY2FsIiwiZ3JvdXAiOlsiQWRtaW5pc3RyYXRvcnMiLCJFdmVyeW9uZSJdLCJleHRfaWF0IjpbIjE3NTIyNjE2OTIiLCIxNzUyMjYxNjkyIl0sInByZWZlcnJlZF91c2VybmFtZV9vaXMiOiJBZG1pbmlzdHJhdG9yIiwic2NoZW1lX29pcyI6InhmbmF0aXZlIiwic2lkIjoiQTQ4NkI3QjNBREQxMTEwODMzRjQ5MzkwRUM2MEQ3OEYiLCJqdGkiOiI2QzY3Q0JCMzE0QUM4NkFEMzRGNTYwMzFEN0Y2NjRFMCJ9.v3Teksl2HQEmFMSjQXyh-ndVbsu3vXbiifwlr_em2qXSGTp5pSCsO85HuYcgvOFyzs82nuSgdNW0MyleTnbgeigZG7pTYG9txEmtU7psjDJmKiZxJSZ8zHO0cdHwCIecV30scSHqCC3Avhd6uY4w65fkOgG7VdE8f1SQNL5pUitdKN6yEIxL0e3YbzXMtxrklM6jw8oghM73hRXBo6gVuuRgXgqciMwyYe36ojmZYNY386dJnnlNEPYt7qoNxRLFZtT7eOEZz9OprCWAIsOmCLEiOkw3gg1o8BTGnMTzzOjaPHQ-i_LZyWvf4EqWg8ye6mzN4aTcJT4BttiLOrW0Jw"
    user_session_info = UserSessionInfo.create_user_session_info_from_jwt(
        env_mode="DEV",
        jwt_access_token=jwt,
        audience="api://wernicke",
        algorithms=["RS256"],
        signing_key=None,
        options=None,
    )

    print(f"🎯 Using token: {user_session_info.access_token[:50]}...")

    thread_id = random.randint(1, 10000)

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

        for question in questions:
            graph_state = CubeViewOrchestratorState(
                user_input=question,
                cube_name="Equipment Division",
                ud_types=ud_types,
                time_scope=TimeScope.SYSTEM_TIME,
            )

            graph_inputs = GraphInputModel(
                graph_state=graph_state,
                thread_id=str(thread_id),
                # hil_responses=[hil_response_1],
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
                results = await orchestrator.arun(inputs=graph_inputs)
                print("--------------------------------------")
                print("Original Query: ", question)
                if results[1] == ResponseType.HIL:
                    print("HIL Response")
                    continue

                # Check for errors in the graph state
                if results[0].graph_state.errors:
                    print("ERRORS DETECTED:")
                    for error in results[0].graph_state.errors:
                        print(f"  - {error}")
                    print("--------------------------------------")
                else:
                    print("No errors detected")

                print(results)

            except NotImplementedError:
                results = [None, None]
            end = time.time()

            # print(f"Orchestrator time: {end - start:.2f}")

            # print(thread_id)
            thread_id += 1

        # for thought in handler._queue.thoughts:
        #     print(json.loads(thought)["system_message"]["message"])

        return None, None


if __name__ == "__main__":
    result, response_type = asyncio.run(execute_orchestrator())
    print(result)
    print(response_type)
    # if response_type == ResponseType.HIL:
    #     for hil_response in result.hil_outputs:
    #         print(hil_response.hil_node_name)
    #         print(hil_response.hil_modality.modality_data.text)
    #         for modal in hil_response.hil_modality.modality_data.options:
    #             print(modal.label)

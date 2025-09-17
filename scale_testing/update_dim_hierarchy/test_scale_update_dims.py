"""
==============================================================================
Name: test_scale_update_dims.py
Author: Aiden Dixon
Date: 9/15/2025
Description: Experimental performance tests to compare updating N dimension
members via Celery task vs HTTP endpoint for hierarchy updates.
==============================================================================
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import List, Tuple

import pytest

pytest_plugins = [
    "wernicke.tests.integration_tests.conftest",
]

from wernicke.config.env_config import env_config_adapter
from wernicke.config.env_config.constants import EnvVar
from wernicke.engines.llm.auxillary.tools.wernicke_tools.models import ExtendedOneStreamDimType
from wernicke.engines.processing.onestream_metadata.constants import COMPANY_SCOPE_ID
from wernicke.engines.processing.onestream_metadata.manager import RubixDimensionManager
from wernicke.engines.processing.onestream_metadata.models import OSUserDefinedDimMember
from wernicke.managers.cosmos_database.azure_cosmos_manager import CosmosDatabaseManager
from wernicke.orchestration import wernicke_celery_manager
from wernicke.orchestration.tasks.store.rubix.t_update_dim_hierarchy import UpdateDimHierarchyTask, UpdateDimHierarchyTaskInputs
from wernicke.tests.integration_tests.app.constants import URL_BASE
from wernicke.tests.shared_constants import celery_await_result


def _generate_ud1_chain(num_members: int, dimension_name: str = "dimension_perf", name_prefix: str = "perf") -> List[OSUserDefinedDimMember]:
    """Generate a simple chain hierarchy of UD1 members of length N.

    The hierarchy is a single path: root -> node_1 -> node_2 -> ... -> node_{N-1}

    Args:
        num_members (int): Number of dimension members to create (>= 1).
        dimension_name (str): The dimension name each member belongs to.
        name_prefix (str): Prefix to use for generated member names.

    Returns:
        List[OSUserDefinedDimMember]: Ordered list of members from root to last leaf.

    Raises:
        ValueError: If num_members is less than 1.
    """
    if num_members < 1:
        raise ValueError("num_members must be >= 1")

    members: List[OSUserDefinedDimMember] = []

    root_name = f"{name_prefix}_root"
    child_name = f"{name_prefix}_node_1" if num_members > 1 else None
    root = OSUserDefinedDimMember(
        name=root_name,
        description=f"{root_name} desc",
        member_id=1_000_000,
        dimensions=[dimension_name],
        dim_type=ExtendedOneStreamDimType.UD1,
        parent_hierarchy="",
        children=[child_name] if child_name else [],
    )
    members.append(root)

    for i in range(1, num_members):
        name = f"{name_prefix}_node_{i}"
        next_child = f"{name_prefix}_node_{i+1}" if (i + 1) < num_members else None
        member = OSUserDefinedDimMember(
            name=name,
            description=f"{name} desc",
            member_id=1_000_000 + i,
            dimensions=[dimension_name],
            dim_type=ExtendedOneStreamDimType.UD1,
            parent_hierarchy=members[-1].name,
            children=[next_child] if next_child else [],
        )
        members.append(member)

    return members


def _upsert_members(user_session_info, members: List[OSUserDefinedDimMember]) -> None:
    """Upsert provided members into Cosmos using RubixDimensionManager.

    Args:
        user_session_info: The test user session info fixture instance.
        members (List[OSUserDefinedDimMember]): Members to upsert.

    Returns:
        None
    """
    with CosmosDatabaseManager(
        user_session_info=user_session_info,
        consistency_level="Strong",
        retry_total=3,
        retry_backoff_max=60,
        retry_connect=3,
        retry_read=3,
    ) as cosmos_database_manager:
        original_connection = user_session_info.database_connection
        try:
            user_session_info.database_connection = cosmos_database_manager
            rubix_dimension_manager = RubixDimensionManager(
                user_session_info=user_session_info,
                database_connection=user_session_info.database_connection,
            )
            rubix_dimension_manager.upsert_dim_members(dim_members=members)
        finally:
            user_session_info.database_connection = original_connection


def _cleanup_members(user_session_info, names: List[str]) -> None:
    """Delete the specified UD1 members by name from Cosmos.

    Args:
        user_session_info: The test user session info fixture instance.
        names (List[str]): Member names to delete.

    Returns:
        None
    """
    original_connection = user_session_info.database_connection
    try:
        with CosmosDatabaseManager(
            user_session_info=user_session_info,
            consistency_level="Strong",
            retry_total=3,
            retry_backoff_max=60,
            retry_connect=3,
            retry_read=3,
        ) as cosmos_database_manager:
            user_session_info.database_connection = cosmos_database_manager
            rubix_dimension_manager = RubixDimensionManager(
                user_session_info=user_session_info,
                database_connection=user_session_info.database_connection,
            )
            for name in names:
                members = rubix_dimension_manager.get_dim_members(dim_type=ExtendedOneStreamDimType.UD1, dim_member_names=[name])
                if members:
                    m = members[0]
                    user_session_info.database_connection.delete_item(
                        container_name=user_session_info.environment_config_adapter.getenv(key=EnvVar.RUBIX_CONTAINER_NAME),
                        item=m.id,
                        partition_key=ExtendedOneStreamDimType.UD1.value,
                    )
    finally:
        user_session_info.database_connection = original_connection


def run_update_hierarchy_timing(
    num_members: int,
    user_session_info,
    client_with_session,
    encoded_auth_jwt: str,
    dimension_name: str = "dimension_perf",
    max_wait_seconds: int = 120,
) -> Tuple[float, float]:
    """Generate N members, upsert them, and time Celery task vs HTTP endpoint.

    The function builds a single-chain UD1 hierarchy of length N under the given
    dimension, upserts the members, then times how long it takes to disable the
    hierarchy starting at the root using the Celery task and the HTTP endpoint.

    Args:
        num_members (int): Number of members to create in the hierarchy (>= 1).
        user_session_info: The test user session info fixture instance.
        client_with_session: FastAPI test client fixture configured with session.
        encoded_auth_jwt (str): Encoded JWT for Authorization header.
        dimension_name (str): Name of the dimension used for all members.
        max_wait_seconds (int): Max seconds to wait for Celery completion.

    Returns:
        Tuple[float, float]: (celery_duration_seconds, endpoint_duration_seconds)
    """
    members = _generate_ud1_chain(num_members=num_members, dimension_name=dimension_name)
    root_name = members[0].name
    member_names = [m.name for m in members]

    _upsert_members(user_session_info=user_session_info, members=members)

    celery_duration = 0.0
    endpoint_duration = 0.0

    try:
        # Time Celery Task
        inputs = UpdateDimHierarchyTaskInputs(
            user_session_info=user_session_info,
            dim_type=ExtendedOneStreamDimType.UD1,
            parent_member_name=root_name,
            disabled=True,
            scope_id=COMPANY_SCOPE_ID,
            dimension_name=dimension_name,
        )
        start = time.perf_counter()
        async_result = wernicke_celery_manager.send_task(
            task=UpdateDimHierarchyTask(
                queue=env_config_adapter.getenv(EnvVar.AZURE_REDIS_QUEUE_NAME),
                ignore_result=False,
            ),
            task_inputs=inputs,
        )
        celery_await_result(task_result=async_result, max_time=max_wait_seconds)
        celery_duration = time.perf_counter() - start

        # Time HTTP Endpoint
        endpoint = URL_BASE + f"/dimensions/{ExtendedOneStreamDimType.UD1.value}/{dimension_name}/members/{root_name}"
        headers = {"Authorization": "Bearer " + encoded_auth_jwt}
        body = {"disabled": True, "scope_id": COMPANY_SCOPE_ID}

        start = time.perf_counter()
        resp = client_with_session.patch(headers=headers, url=endpoint, json=body)
        assert resp.status_code == 200, resp.text
        endpoint_duration = time.perf_counter() - start

        # Verify all nodes are disabled at the company scope
        original_connection = user_session_info.database_connection
        try:
            with CosmosDatabaseManager(
                user_session_info=user_session_info,
                consistency_level="Strong",
                retry_total=3,
                retry_backoff_max=60,
                retry_connect=3,
                retry_read=3,
            ) as cosmos_database_manager:
                user_session_info.database_connection = cosmos_database_manager
                rubix_dimension_manager = RubixDimensionManager(
                    user_session_info=user_session_info,
                    database_connection=user_session_info.database_connection,
                )
                for name in member_names:
                    member = rubix_dimension_manager.get_dim_members(dim_type=ExtendedOneStreamDimType.UD1, dim_member_names=[name])[0]
                    assert member.disabled_dict.get(COMPANY_SCOPE_ID) is True
        finally:
            user_session_info.database_connection = original_connection

    finally:
        _cleanup_members(user_session_info=user_session_info, names=member_names)

    return celery_duration, endpoint_duration


@pytest.mark.parametrize("num_members", [10, 100, 500, 1000, 5000, 10000, 20000])
def test_scale_update_dim_hierarchy(
    num_members,
    return_user_session_info,
    create_test_database,
    create_test_table_storage_tables,
    client_with_session,
    return_encoded_auth_jwt,
):
    """Scale test to time Celery task vs HTTP endpoint for N members.

    Args:
        num_members (int): Parametrized number of members to generate in chain.
        return_user_session_info: Fixture providing user session info object.
        create_test_database: Fixture ensuring test Cosmos DB is available.
        create_test_table_storage_tables: Fixture ensuring table storage is available.
        client_with_session: Fixture providing an authenticated FastAPI client.
        return_encoded_auth_jwt: Fixture providing encoded JWT string.

    Returns:
        None
    """
    celery_s, endpoint_s = run_update_hierarchy_timing(
        num_members=num_members,
        user_session_info=return_user_session_info,
        client_with_session=client_with_session,
        encoded_auth_jwt=return_encoded_auth_jwt,
        dimension_name="dimension_perf",
        max_wait_seconds=300,
    )

    # Emit timings for visibility during test runs
    print(f"UpdateDimHierarchy N={num_members} -> Celery: {celery_s:.4f}s | Endpoint: {endpoint_s:.4f}s")

    # Write timings to CSV in the same directory as this test file
    results_path = Path(__file__).parent / "scale_update_dim_timings.csv"
    write_header = not results_path.exists()
    with results_path.open(mode="a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["num_members", "celery_seconds", "endpoint_seconds"])
        writer.writerow([num_members, f"{celery_s:.6f}", f"{endpoint_s:.6f}"])
    print(f"Wrote timings to: {results_path}")

    assert celery_s >= 0.0
    assert endpoint_s >= 0.0

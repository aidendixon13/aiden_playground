import asyncio
import json
import os
from unittest.mock import patch

from wernicke.engines.auth.auth_manager import AuthManager
from wernicke.engines.llm.auxillary.tools.wernicke_tools.models import (
    CoreOneStreamDimType,
    ExtendedOneStreamDimType,
)
from wernicke.engines.processing.onestream_client.store.expansion_count import (
    ExpansionCountService,
)
from wernicke.engines.processing.onestream_metadata.manager import RubixDimensionManager
from wernicke.internals.session.user_session import UserSessionInfo
from wernicke.managers.cosmos_database.azure_cosmos_manager import CosmosDatabaseManager
from wernicke.tests.mocks.onestream_metadata.expansion_count.expansion_count import (
    MockExpansionCountService,
)
from wernicke.tests.shared_utils.test_jwt import decode_test_jwt
from wernicke.tests.shared_utils.test_session import create_test_user_session


def extract_between_hash_and_dot(input_string: str) -> str:
    """
    Extract the part between '#' and '.' from a string.

    Args:
        input_string (str): String like 'A#60999.Children'

    Returns:
        str: The extracted part (e.g., '60999')

    Raises:
        ValueError: If '#' or '.' is not found in the string
    """
    if "#" not in input_string or "." not in input_string:
        raise ValueError(f"String must contain both '#' and '.': {input_string}")

    hash_index = input_string.find("#")
    dot_index = input_string.find(".")

    if hash_index >= dot_index:
        raise ValueError(f"'#' must come before '.': {input_string}")

    return input_string[hash_index + 1 : dot_index]


def load_expansion_count_json(json_file_path: str) -> list:
    """Load existing expansion count data from JSON file."""
    if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
        with open(json_file_path, "r") as f:
            return json.load(f)
    return []


def save_expansion_count_json(json_file_path: str, data: list) -> None:
    """Save expansion count data to JSON file."""
    with open(json_file_path, "w") as f:
        json.dump(data, f, indent=2)


def entry_exists(existing_data: list, dim_member: str, expansion: str) -> bool:
    """Check if an entry already exists in the JSON data."""
    for entry in existing_data:
        if entry.get("dim_member") == dim_member and entry.get("expansion") == expansion:
            return True
    return False


async def main():
    # Also create mock service to check if data already exists in JSON

    jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijk2MkNEN0ZEMzRDQzQ0ODBFNjA0NDNBNkY0NUEwNjVDIiwieDV0IjoiRTBJSkFhdlFTZWpEbDg2ZVo1T2ZQSmFSMW9JIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2xvY2FsaG9zdDo0NDM4NyIsIm5iZiI6MTc1NTExNDgxOSwiaWF0IjoxNzU1MTE0ODE5LCJleHAiOjE3NTUxMTg0MTksImF1ZCI6ImFwaTovL3dlcm5pY2tlIiwic2NvcGUiOlsib3BlbmlkIiwiZW1haWwiLCJwcm9maWxlIiwiZ3JvdXBzIiwiYXBpOi8vd2Vybmlja2Uvd2Vybmlja2UuYWxsIiwib2ZmbGluZV9hY2Nlc3MiXSwiYW1yIjpbInB3ZCJdLCJjbGllbnRfaWQiOiJzZW5zaWJsZWdlbmFpLnBob2VuaXgiLCJzdWIiOiI2ZjM3M2RlNC1jOWJmLTRlYzMtOGI2Ny01YzExZjIwYjViNWUiLCJhdXRoX3RpbWUiOjE3NTUxMTA2NzAsImlkcCI6ImxvY2FsIiwiZ3JvdXAiOlsiQWRtaW5pc3RyYXRvcnMiLCJFdmVyeW9uZSJdLCJleHRfaWF0IjpbIjE3NTUxMTQ4MTkiLCIxNzU1MTE0ODE5Il0sInByZWZlcnJlZF91c2VybmFtZV9vaXMiOiJBZG1pbmlzdHJhdG9yIiwic2NoZW1lX29pcyI6InhmbmF0aXZlIiwic2lkIjoiNEFFNjlGRThBNjM0RTEzMEREOUQ3Q0QzRTVFODM3OTQiLCJqdGkiOiJGREMwRUFDRkNDRUZFNEM2NDg4REU3Q0VCRjcwNzc4RiJ9.0bE011r6kEjGA8HXu2XI-23Ba8R5QH9KusTeTRgMWjzFFhNyZKBBmSKHd_lQ55FMSVcYUJzjHlmjy3pDscCYNIN23sHpZLc47x6dMcdNYcQcEBypbg7WPnfjuhm4xEdtqEGuzzC67oKCevgoXpM0VvHqKKujRkwRI8oatl57TkOMl4hC3cNjJ1GBC-pF1N3tn9UiDrFOoT-GB_zUfqK3TAZDPAfSs4uhn8cxcQo7ZlanOIr6aR6Q0i72Kge48Qcfqk_AXns4JXBBE10oABuuEVcRg8fbHNDNZ81tUzwNnpnR4ccKXMDA2kQ1WyjpxTRGBF08r6F8uYbB50od6GOQFA"

    user_session_info = await AuthManager.create_session_from_jwt_token(jwt_token=jwt)

    expansions = [".Base", ".Tree", ".ChildrenInclusive", ".Children"]
    # expansions.append(".TreeDescendantsR")

    with CosmosDatabaseManager(user_session_info=user_session_info) as database_connection:
        user_session_info.database_connection = database_connection
        rubix_dimension_manager = RubixDimensionManager(
            user_session_info=user_session_info,
            database_connection=user_session_info.database_connection,
        )

        # Use real ExpansionCountService to get actual data from the API
        expansion_count_service = ExpansionCountService(user_session_info=user_session_info)

        # Also create mock service to check if data already exists in JSON
        mock_expansion_count_service = MockExpansionCountService(user_session_info=user_session_info)

        prefix_to_dim_type = {
            "A#": CoreOneStreamDimType.ACCOUNT,
            "S#": CoreOneStreamDimType.SCENARIO,
            "F#": CoreOneStreamDimType.FLOW,
            "E#": CoreOneStreamDimType.ENTITY,
            "U1#": ExtendedOneStreamDimType.UD1,
            "U2#": ExtendedOneStreamDimType.UD2,
            "U3#": ExtendedOneStreamDimType.UD3,
            "U4#": ExtendedOneStreamDimType.UD4,
            "U5#": ExtendedOneStreamDimType.UD5,
            "U6#": ExtendedOneStreamDimType.UD6,
        }

        # Define the dimension member you want to get expansion counts for
        dimension_member = "U3#PRD120"  # Just specify the dimension member without expansion

        # Find the matching prefix (handle variable length prefixes)
        dim_type = None
        for prefix, dtype in prefix_to_dim_type.items():
            if dimension_member.startswith(prefix):
                dim_type = dtype
                break

        if dim_type is None:
            raise ValueError(f"No matching dimension type found for dimension member: {dimension_member}")

        # Extract the part after # using the helper function (but modify for this use case)
        extracted_name = dimension_member.split("#")[1] if "#" in dimension_member else dimension_member
        print(f"Dimension member: {dimension_member}")
        print(f"Extracted name: {extracted_name}")
        print(f"Dimension type: {dim_type}")

        dim_members = rubix_dimension_manager.get_dim_members(dim_member_names=[extracted_name], dim_type=dim_type)
        print(f"Found dim members: {dim_members}")

        # Load existing JSON data
        json_file_path = "source/wernicke/tests/mocks/onestream_metadata/expansion_count/expansion_count.json"
        existing_data = load_expansion_count_json(json_file_path)
        print(f"Loaded {len(existing_data)} existing entries from JSON")

        # Get expansion counts for all expansions in the list
        expansion_results = {}
        new_entries = []

        for dim_member in dim_members:
            print(f"\n--- Processing dimension member: {dim_member.name} ---")
            expansion_results[dim_member.name] = {}

            for expansion in expansions:
                full_expansion_name = f"{dimension_member}{expansion}"

                # Check if entry already exists in JSON using mock service
                try:
                    existing_count = mock_expansion_count_service.get_member_expansion_count(
                        member_expansion=full_expansion_name,
                        potential_dim_names=dim_member.dimensions,
                    )
                    print(f"  {full_expansion_name}: Already exists in JSON ({existing_count}) - skipping")
                    expansion_results[dim_member.name][expansion] = f"Already exists ({existing_count})"
                    continue
                except ValueError:
                    # Entry doesn't exist in JSON, so we need to fetch it
                    pass

                try:
                    # Use real service to get actual expansion count from API
                    expansion_count = expansion_count_service.get_member_expansion_count(
                        member_expansion=full_expansion_name,
                        potential_dim_names=dim_member.dimensions,
                    )
                    expansion_results[dim_member.name][expansion] = expansion_count
                    print(f"  {full_expansion_name}: {expansion_count} - NEW ENTRY")

                    # Add to new entries list
                    new_entry = {"dim_member": dimension_member, "expansion": expansion, "expansion_count": expansion_count}
                    new_entries.append(new_entry)

                except Exception as e:
                    expansion_results[dim_member.name][expansion] = f"Error: {str(e)}"
                    print(f"  {full_expansion_name}: Error - {str(e)}")

        # Add new entries to existing data and save
        if new_entries:
            existing_data.extend(new_entries)
            save_expansion_count_json(json_file_path, existing_data)
            print(f"\n✅ Added {len(new_entries)} new entries to JSON file")
        else:
            print(f"\n✅ No new entries to add - all expansions already exist in JSON")

        # Print summary
        print(f"\n=== SUMMARY ===")
        for member_name, expansions_dict in expansion_results.items():
            print(f"\nDimension Member: {member_name}")
            for expansion, count in expansions_dict.items():
                print(f"  {expansion}: {count}")


if __name__ == "__main__":
    asyncio.run(main())

"""
Scratch test file for testing the expand_rowcol endpoint with cube view artifacts.
"""

import asyncio
import json
import os

from DataAnalysisService import DataAnalysisService
from models import POV

from wernicke.engines.auth.auth_manager import AuthManager


async def main():
    """
    Main function to test the DataAnalysisService.post_expand_rowcol() method with cube view artifacts.
    """
    # JWT token for authentication
    jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6IkJBRDgzOEZBRjI0MjUyQ0E2Q0YwMkJFMjA5QjQyQzY4IiwieDV0IjoidU1mUVk0WlhVQXZacUZkSTh6eFdaT0VhQkJnIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2xvY2FsaG9zdDo0NDM4NyIsIm5iZiI6MTc2MDQ1MTE0NywiaWF0IjoxNzYwNDUxMTQ3LCJleHAiOjE3NjA0NTQ3NDcsImF1ZCI6ImFwaTovL3dlcm5pY2tlIiwic2NvcGUiOlsib3BlbmlkIiwiZW1haWwiLCJwcm9maWxlIiwiZ3JvdXBzIiwiYXBpOi8vd2Vybmlja2Uvd2Vybmlja2UuYWxsIiwib2ZmbGluZV9hY2Nlc3MiXSwiYW1yIjpbInB3ZCJdLCJjbGllbnRfaWQiOiJzZW5zaWJsZWdlbmFpLnBob2VuaXgiLCJzdWIiOiJlMjI1OWZmNC1iYTA2LTQ2NDEtOWIxMC1jMTNhYmU5ZGY4NWMiLCJhdXRoX3RpbWUiOjE3NjA0NDc5NjMsImlkcCI6ImxvY2FsIiwiZ3JvdXAiOlsiQWRtaW5pc3RyYXRvcnMiLCJDX0Nsb3VkIiwiQ19DdXN0b21lciIsIkNfRmluUmVwb3J0aW5nIiwiQ19WZW5kb3IiLCJEX0FjY291bnRpbmciLCJEX0FkbWluIiwiRF9BSURlbGl2ZXJ5IiwiRF9BSURlbWFuZCIsIkRfQUlQcm9kRW5naW5lZXJpbmciLCJEX0FMTCIsIkRfQXJjaEZhY3RvcnkiLCJEX0FURyIsIkRfQnVzRGV2IiwiRF9CdXNEZXZfRU1FQSIsIkRfQnVzRGV2X05BIiwiRF9CdXNPcHMiLCJEX0Nsb3VkRGV2IiwiRF9DbG91ZE9wcyIsIkRfQ29tbWVyY2lhbFN0cmF0IiwiRF9Db25zdWx0U3ZjcyIsIkRfQ29uc3VsdFN2Y3NfRU1FQSIsIkRfQ29uc3VsdFN2Y3NfTkEiLCJEX0N1c3RTdWNjZXNzIiwiRF9DdXN0U3VwcG9ydCIsIkRfRERNa3RnIiwiRF9EZW1vRW5naW5lZXJpbmciLCJEX0VkdWNhdGlvblN2Y3MiLCJEX0VQTSIsIkRfRXZlbnRNZ210IiwiRF9GYWNpbGl0aWVzIiwiRF9GaW5hbmNlIiwiRF9IUiIsIkRfSW5mb1NlY3VyaXR5IiwiRF9JbmZvU3lzIiwiRF9JVCIsIkRfTGVnYWwiLCJEX01nbXQxIiwiRF9NZ210MTAiLCJEX01nbXQxMSIsIkRfTWdtdDEyIiwiRF9NZ210MTMiLCJEX01nbXQxNCIsIkRfTWdtdDIiLCJEX01nbXQzIiwiRF9NZ210NCIsIkRfTWdtdDUiLCJEX01nbXQ2IiwiRF9NZ210NyIsIkRfTWdtdDgiLCJEX01nbXQ5IiwiRF9Na3RQbGFjZURldiIsIkRfUEUiLCJEX1BFX0FQQUMiLCJEX1BFX0VNRUEiLCJEX1BFX05BIiwiRF9QbGF0RGV2IiwiRF9QbGF0Zm9ybUFyY2giLCJEX1ByZXNhbGVzIiwiRF9Qcm9kQ29tbSIsIkRfUHJvZEN1c3RFeHBNa3RnIiwiRF9Qcm9kTWdtdCIsIkRfUkMiLCJEX1Jpc2siLCJEX1NhbGVzIiwiRF9TYWxlc19BUEFDIiwiRF9TYWxlc19FTUVBIiwiRF9TYWxlc19OQSIsIkRfU2FsZXNFbmFibGUiLCJEX1NhbGVzT3BzIiwiRF9Tb2x1dGlvbk5ldHdvcmsiLCJEX1N0cmF0QWxsaWFuY2VzIiwiRF9TdHJhdENvbW1zIiwiREJfQnVzaW5lc3NQYXJ0bmVycyIsIkRCX0ZpbmFuY2UiLCJEcmlsbGl0X0FjY2VzcyIsIkVfQWxsX1JlYWQiLCJFX0FsbF9Xcml0ZSIsIkV2ZXJ5b25lIiwiRXZlcnlvbmVFeGNlcHRSZWFkT25seVVzZXJzIiwiSGVscF9IZWxwRGVza0VtYWlsIiwiT3Blbl9CYWNrdXBBcHAiLCJQb3dlclVzZXJzIiwiUl9DdWJlVmlld3MiLCJSX0RpbWVuc2lvbkxpYnJhcnkiLCJSX0ZYUmF0ZXMiLCJSX0pvdXJuYWxUZW1wbGF0ZXMiLCJSX1RhYmxlVmlld3MiLCJSX1RyYW5zUnVsZSIsIlJDTV9WaWV3IiwiU19BY3R1YWxfUmVhZCIsIlNfQWN0dWFsX1dyaXRlIiwiU19QbGFubmluZ19SZWFkIiwiU19QbGFubmluZ19Xcml0ZSIsIlNfU3RhdHV0b3J5X1JlYWQiLCJTX1N0YXR1dG9yeV9Xcml0ZSIsInN5c3RlbUFkbWlucyIsIlRNXzAxIiwiVE1fMDIiLCJUTV8wMyIsIlRNXzA0IiwiVE1fMDUiLCJUTV8wNiIsIlRNXzA3IiwiVE1fMDgiLCJUTV8wOSIsIlRNXzEwIiwiVE1fQWRtaW4iLCJUTV9Vc2VycyIsIlRvb2xLaXRfQWNjZXNzIl0sImV4dF9pYXQiOlsiMTc2MDQ1MTE0NyIsIjE3NjA0NTExNDciXSwicHJlZmVycmVkX3VzZXJuYW1lX29pcyI6IlRlc3QgVXNlciAxIiwic2NoZW1lX29pcyI6InhmbmF0aXZlIiwic2lkIjoiNjEzMURENzI2MkE3RjhFQjU0OEY3NkMzMEQ2OTRDODEiLCJqdGkiOiJCQ0Q5N0IyMzc2NUZCMkE0MEVFRTdBMTI4QkRCNEMyNSJ9.cBFaPxS1AOH87kdj3CxGSSKcpAbHXrk6Jm8Ge5keX--0fHdA21_mgu9F9pzycTjQM38Rov3cIygBMPA3tHk0iLg6nu3GriXpKA5rBXmA7VG8M3VOF-AfIw5b0hmFa-VjqXXWDO9AB3roDlk4yKu01sZmNLS1uoapTMQGWuKyt68sGMR9PJ3qlvANgQVmryyuSD54-DtaiObPHCA8DgzzSahA7KhUb_7nDIFNc30iQFScVEQ8KR5n3dZoQPRMb_PFTMsds3r7-YG0sO-uNP9fzSQc4N5maL2AE-u3hfX-jAS9mMA7881CC1S56EOch3JbIJjMdQSvGeTHgiUTFvSc7w"

    # Create a test user session from JWT
    print("Creating test user session from JWT...")
    user_session_info = await AuthManager.create_session_from_jwt_token(jwt_token=jwt)

    # Initialize the DataAnalysisService
    print("Initializing DataAnalysisService...")
    service = DataAnalysisService(user_session_info=user_session_info)

    # Load cube view artifacts from JSON file
    print(f"\n{'='*80}")
    print("Loading cube view artifacts from JSON file...")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(script_dir, "cube_view_artifacts.json")

    with open(json_file_path, "r") as f:
        data = json.load(f)

    # Loop through the artifacts
    for artifact_dict in data["cube_view_artifacts"]:
        artifact_data = artifact_dict["artifact_data"]

        print(f"\n{'='*80}")
        print(f"Processing artifact: {artifact_dict['id']}")

        # Extract POV data
        pov_data = artifact_data["pov"]
        pov = POV(
            CubeName=pov_data["cube_name"],
            Entity=pov_data["entity"],
            Parent=pov_data["parent"],
            Consolidation=pov_data["consolidation"],
            Scenario=pov_data["scenario"],
            Time=pov_data["time"],
            View=pov_data["view"],
            Account=pov_data["account"],
            Flow=pov_data["flow"],
            Origin=pov_data["origin"],
            IC=pov_data["ic"],
            UD1=pov_data["ud1"],
            UD2=pov_data["ud2"],
            UD3=pov_data["ud3"],
            UD4=pov_data["ud4"],
            UD5=pov_data["ud5"],
            UD6=pov_data["ud6"],
            UD7=pov_data["ud7"],
            UD8=pov_data["ud8"],
        )

        # Convert POV to dict for sending
        pov_dict = json.loads(pov.model_dump_json(by_alias=True))

        print(f"\nPOV:")
        print(f"  Cube: {pov_data['cube_name']}")
        print(f"  Entity: {pov_data['entity']}")
        print(f"  Scenario: {pov_data['scenario']}")
        print(f"  Time: {pov_data['time']}")

        # Collect all row_column members from rows and columns
        all_members = []

        # Process rows
        if "rows" in artifact_data:
            for row in artifact_data["rows"]:
                for member_str in row["row_column"]:
                    all_members.append({"source": "row", "primary_dimension": row["primary_dimension"], "member": member_str})

        # Process columns
        if "columns" in artifact_data:
            for col in artifact_data["columns"]:
                for member_str in col["row_column"]:
                    all_members.append({"source": "column", "primary_dimension": col["primary_dimension"], "member": member_str})

        print(f"\nFound {len(all_members)} member(s) to expand")

        # Call expand_rowcol endpoint for each member
        for idx, member_info in enumerate(all_members, 1):
            member_str = member_info["member"]
            print(f"\n{'-'*80}")
            print(f"Expanding member {idx}/{len(all_members)}: {member_str}")
            print(f"  Source: {member_info['source']}")
            print(f"  Primary Dimension: {member_info['primary_dimension']}")

            # Parse the member string (e.g., "E#NAE.Base") into DimensionMember format
            if "#" in member_str:
                dim_prefix = member_str.split("#")[0]
                rest = member_str.split("#")[1]

                # Map prefix to dimension type
                dim_type_map = {
                    "E": "Entity",
                    "T": "Time",
                    "A": "Account",
                    "S": "Scenario",
                    "F": "Flow",
                    "O": "Origin",
                    "I": "IC",
                    "P": "Parent",
                    "C": "Consolidation",
                    "V": "View",
                    "U1": "UD1",
                    "U2": "UD2",
                    "U3": "UD3",
                    "U4": "UD4",
                    "U5": "UD5",
                    "U6": "UD6",
                    "U7": "UD7",
                    "U8": "UD8",
                }

                dim_type = dim_type_map.get(dim_prefix, dim_prefix)

                # Parse member name and expansion
                if "." in rest:
                    member_name = rest.split(".")[0]
                    expansion = rest.split(".")[1]
                    # Create DimensionMember object with expansion
                    dimension_member = {"DimType": dim_type, "DimName": member_name, "Expansion": expansion, "Level": 0}
                    print(f"  Parsed DimensionMember: {dim_type}#{member_name}.{expansion}")
                else:
                    member_name = rest
                    # Create DimensionMember object without expansion
                    dimension_member = {"DimType": dim_type, "DimName": member_name, "Level": 0}
                    print(f"  Parsed DimensionMember: {dim_type}#{member_name}")
            else:
                print(f"  ⚠️ Skipping invalid member format: {member_str}")
                continue

            # Build the expand request - Members should be a list
            expand_request = {"Pov": pov_dict, "Members": [dimension_member]}

            print(f"\nExpand Request:")
            print(json.dumps(expand_request, indent=2))

            # Send the request
            try:
                result = service.post_expand_rowcol(expand_request)
                print(f"\n✅ Expansion Response:")
                print(json.dumps(result, indent=2))
            except Exception as e:
                print(f"\n❌ Error expanding member: {str(e)}")

    print(f"\n{'='*80}")
    print("✅ Finished processing all artifacts!")


if __name__ == "__main__":
    asyncio.run(main())

"""
Scratch test file for DataAnalysisService
"""

import asyncio
import json
import os

from DataAnalysisService import DataAnalysisService
from models import POV, AnalysisType, BaseFilter, BaseSort, DimensionMember

from wernicke.engines.auth.auth_manager import AuthManager
from wernicke.engines.llm.auxillary.artifacts.store.cube_view_artifact import DynamicReportArtifact


async def main():
    """
    Main function to test the DataAnalysisService.get_hello() method and load cube view artifacts.
    """
    # JWT token for authentication
    jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6IkJBRDgzOEZBRjI0MjUyQ0E2Q0YwMkJFMjA5QjQyQzY4IiwieDV0IjoidU1mUVk0WlhVQXZacUZkSTh6eFdaT0VhQkJnIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2xvY2FsaG9zdDo0NDM4NyIsIm5iZiI6MTc2MDQ3OTA4OSwiaWF0IjoxNzYwNDc5MDg5LCJleHAiOjE3NjA0ODI2ODksImF1ZCI6ImFwaTovL3dlcm5pY2tlIiwic2NvcGUiOlsib3BlbmlkIiwiZW1haWwiLCJwcm9maWxlIiwiZ3JvdXBzIiwiYXBpOi8vd2Vybmlja2Uvd2Vybmlja2UuYWxsIiwib2ZmbGluZV9hY2Nlc3MiXSwiYW1yIjpbInB3ZCJdLCJjbGllbnRfaWQiOiJzZW5zaWJsZWdlbmFpLnBob2VuaXgiLCJzdWIiOiJlMjI1OWZmNC1iYTA2LTQ2NDEtOWIxMC1jMTNhYmU5ZGY4NWMiLCJhdXRoX3RpbWUiOjE3NjA0NzkwODgsImlkcCI6ImxvY2FsIiwiZ3JvdXAiOlsiQWRtaW5pc3RyYXRvcnMiLCJDX0Nsb3VkIiwiQ19DdXN0b21lciIsIkNfRmluUmVwb3J0aW5nIiwiQ19WZW5kb3IiLCJEX0FjY291bnRpbmciLCJEX0FkbWluIiwiRF9BSURlbGl2ZXJ5IiwiRF9BSURlbWFuZCIsIkRfQUlQcm9kRW5naW5lZXJpbmciLCJEX0FMTCIsIkRfQXJjaEZhY3RvcnkiLCJEX0FURyIsIkRfQnVzRGV2IiwiRF9CdXNEZXZfRU1FQSIsIkRfQnVzRGV2X05BIiwiRF9CdXNPcHMiLCJEX0Nsb3VkRGV2IiwiRF9DbG91ZE9wcyIsIkRfQ29tbWVyY2lhbFN0cmF0IiwiRF9Db25zdWx0U3ZjcyIsIkRfQ29uc3VsdFN2Y3NfRU1FQSIsIkRfQ29uc3VsdFN2Y3NfTkEiLCJEX0N1c3RTdWNjZXNzIiwiRF9DdXN0U3VwcG9ydCIsIkRfRERNa3RnIiwiRF9EZW1vRW5naW5lZXJpbmciLCJEX0VkdWNhdGlvblN2Y3MiLCJEX0VQTSIsIkRfRXZlbnRNZ210IiwiRF9GYWNpbGl0aWVzIiwiRF9GaW5hbmNlIiwiRF9IUiIsIkRfSW5mb1NlY3VyaXR5IiwiRF9JbmZvU3lzIiwiRF9JVCIsIkRfTGVnYWwiLCJEX01nbXQxIiwiRF9NZ210MTAiLCJEX01nbXQxMSIsIkRfTWdtdDEyIiwiRF9NZ210MTMiLCJEX01nbXQxNCIsIkRfTWdtdDIiLCJEX01nbXQzIiwiRF9NZ210NCIsIkRfTWdtdDUiLCJEX01nbXQ2IiwiRF9NZ210NyIsIkRfTWdtdDgiLCJEX01nbXQ5IiwiRF9Na3RQbGFjZURldiIsIkRfUEUiLCJEX1BFX0FQQUMiLCJEX1BFX0VNRUEiLCJEX1BFX05BIiwiRF9QbGF0RGV2IiwiRF9QbGF0Zm9ybUFyY2giLCJEX1ByZXNhbGVzIiwiRF9Qcm9kQ29tbSIsIkRfUHJvZEN1c3RFeHBNa3RnIiwiRF9Qcm9kTWdtdCIsIkRfUkMiLCJEX1Jpc2siLCJEX1NhbGVzIiwiRF9TYWxlc19BUEFDIiwiRF9TYWxlc19FTUVBIiwiRF9TYWxlc19OQSIsIkRfU2FsZXNFbmFibGUiLCJEX1NhbGVzT3BzIiwiRF9Tb2x1dGlvbk5ldHdvcmsiLCJEX1N0cmF0QWxsaWFuY2VzIiwiRF9TdHJhdENvbW1zIiwiREJfQnVzaW5lc3NQYXJ0bmVycyIsIkRCX0ZpbmFuY2UiLCJEcmlsbGl0X0FjY2VzcyIsIkVfQWxsX1JlYWQiLCJFX0FsbF9Xcml0ZSIsIkV2ZXJ5b25lIiwiRXZlcnlvbmVFeGNlcHRSZWFkT25seVVzZXJzIiwiSGVscF9IZWxwRGVza0VtYWlsIiwiT3Blbl9CYWNrdXBBcHAiLCJQb3dlclVzZXJzIiwiUl9DdWJlVmlld3MiLCJSX0RpbWVuc2lvbkxpYnJhcnkiLCJSX0ZYUmF0ZXMiLCJSX0pvdXJuYWxUZW1wbGF0ZXMiLCJSX1RhYmxlVmlld3MiLCJSX1RyYW5zUnVsZSIsIlJDTV9WaWV3IiwiU19BY3R1YWxfUmVhZCIsIlNfQWN0dWFsX1dyaXRlIiwiU19QbGFubmluZ19SZWFkIiwiU19QbGFubmluZ19Xcml0ZSIsIlNfU3RhdHV0b3J5X1JlYWQiLCJTX1N0YXR1dG9yeV9Xcml0ZSIsInN5c3RlbUFkbWlucyIsIlRNXzAxIiwiVE1fMDIiLCJUTV8wMyIsIlRNXzA0IiwiVE1fMDUiLCJUTV8wNiIsIlRNXzA3IiwiVE1fMDgiLCJUTV8wOSIsIlRNXzEwIiwiVE1fQWRtaW4iLCJUTV9Vc2VycyIsIlRvb2xLaXRfQWNjZXNzIl0sImV4dF9pYXQiOlsiMTc2MDQ3OTA4OSIsIjE3NjA0NzkwODkiXSwicHJlZmVycmVkX3VzZXJuYW1lX29pcyI6IlRlc3QgVXNlciAxIiwic2NoZW1lX29pcyI6InhmbmF0aXZlIiwic2lkIjoiOUQyODBFQTJFNDZBNDExQUIwM0UyRDk0MEY0QjY0MUIiLCJqdGkiOiI0QUIzMjg1QTU4NUZGODZEMTVBMTc3Mzk4Q0E3MzE2MiJ9.aI01V1LZnKbPMPhxKUnrzMisrLWqa_POHoPXQq6ZBB_EJ-piz2Q15BPmgFOfNGUEFr25S7iAF0G3Xb7_T6G4M8od9PRkzwxFvjL4dkn-ppCxhdV084NhHnJx0qQ4K2MUa88tnz3xjyh5ApfpWnrXdIg2vLCwRWisQX8rXC4pVZM3FLQcORlJeEnEK2AIrrs9by88uPe5ywQi71DrYJHyzf_Tk1yORYB8xO7eW34Fs-Jk5x_RJgpFEVAXMUXxRA6YfBi50twVGmNQitrG4hH2PQX6IsNwmwlquge5LcyvFDPnOinL3wa6RXBjOoMAb7tmdw8PON6P4WR0SZO9vVzLYw"

    # Create a test user session from JWT
    print("Creating test user session from JWT...")
    user_session_info = await AuthManager.create_session_from_jwt_token(jwt_token=jwt)

    # Initialize the DataAnalysisService
    print("Initializing DataAnalysisService...")
    service = DataAnalysisService(user_session_info=user_session_info)

    # Load cube view artifacts from JSON file
    print("\n" + "=" * 80)
    print("Loading cube view artifacts from JSON file...")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(script_dir, "cube_view_artifacts.json")

    with open(json_file_path, "r") as f:
        data = json.load(f)

    # Loop through the artifacts and create DynamicReportArtifact objects
    artifacts = []
    all_analysis_steps = []

    for artifact_dict in data["cube_view_artifacts"]:
        # Extract and remove analysis_steps, Members, and target_rowCol from artifact_data (they're not part of DynamicReportArtifact)
        artifact_data = artifact_dict["artifact_data"].copy()
        analysis_steps_data = artifact_data.pop("analysis_steps", [])
        members_data = artifact_data.pop("Members", [])
        target_rowcol = artifact_data.pop("target_rowCol", "")

        # Filter out Cosmos DB metadata fields
        filtered_artifact = {
            "id": artifact_dict["id"],
            "user_id": artifact_dict["user_id"],
            "artifact_type": artifact_dict["artifact_type"],
            "artifact_data": artifact_data,
        }

        # Create the DynamicReportArtifact object using Pydantic validation
        artifact = DynamicReportArtifact(**filtered_artifact)
        artifacts.append(artifact)

        print(f"\nLoaded artifact {artifact.id}:")
        print(f"  User ID: {artifact.user_id}")
        print(f"  Type: {artifact.artifact_type}")
        print(f"  Rows: {len(artifact.artifact_data.rows) if artifact.artifact_data else 0}")
        print(f"  Columns: {len(artifact.artifact_data.columns) if artifact.artifact_data else 0}")
        if artifact.artifact_data and artifact.artifact_data.pov:
            print(f"  Cube Name: {artifact.artifact_data.pov.cube_name}")

        # Process analysis steps separately
        if analysis_steps_data:
            print(f"\n  Analysis Steps for artifact {artifact.id}:")
            artifact_steps = []
            for step_data in analysis_steps_data:
                # Determine the correct model based on AnalysisType
                analysis_type = AnalysisType(step_data["AnalysisType"])

                if analysis_type == AnalysisType.SORT:
                    step = BaseSort(**step_data)
                    print(f"    - {step.analysis_type.value}: Order={step.order.value}, NullHandle={step.null_handle.value}")
                elif analysis_type == AnalysisType.FILTER:
                    step = BaseFilter(**step_data)
                    filter_details = f"Condition='{step.condition}'"
                    if step.filter_type:
                        filter_details += f", Type={step.filter_type.value}"
                    if step.value is not None:
                        filter_details += f", Value={step.value}"
                    if step.text_value:
                        filter_details += f", TextValue='{step.text_value}'"
                    filter_details += f", Include={step.include}"
                    print(f"    - {step.analysis_type.value}: {filter_details}")
                else:
                    # For other types, use the base class
                    from models import BaseAnalysisObject

                    step = BaseAnalysisObject(**step_data)
                    print(f"    - {step.analysis_type.value}")

                artifact_steps.append(step)

            all_analysis_steps.append({"artifact_id": artifact.id, "steps": artifact_steps, "members": members_data, "target_rowcol": target_rowcol})

    print(f"\n{'='*80}")
    print(f"✅ Successfully loaded {len(artifacts)} cube view artifact(s)!")
    print(f"✅ Successfully loaded {sum(len(item['steps']) for item in all_analysis_steps)} analysis step(s)!")

    # Build and send analysis request for each artifact
    if artifacts and all_analysis_steps:
        for idx, (artifact, analysis_data) in enumerate(zip(artifacts, all_analysis_steps), 1):
            print(f"\n{'='*80}")
            print(f"Building Analysis Request for Artifact {idx}/{len(artifacts)}...")
            print(f"Artifact ID: {artifact.id}")

            steps = analysis_data["steps"]
            members_data = analysis_data["members"]
            target_rowcol = analysis_data["target_rowcol"]

            # Build POV from artifact
            pov_data = artifact.artifact_data.pov
            pov = POV(
                CubeName=pov_data.cube_name,
                Entity=pov_data.entity,
                Parent=pov_data.parent,
                Consolidation=pov_data.consolidation,
                Scenario=pov_data.scenario,
                Time=pov_data.time,
                View=pov_data.view,
                Account=pov_data.account,
                Flow=pov_data.flow,
                Origin=pov_data.origin,
                IC=pov_data.ic,
                UD1=pov_data.ud1,
                UD2=pov_data.ud2,
                UD3=pov_data.ud3,
                UD4=pov_data.ud4,
                UD5=pov_data.ud5,
                UD6=pov_data.ud6,
                UD7=pov_data.ud7,
                UD8=pov_data.ud8,
            )

            # Convert members data to DimensionMember objects
            members = [DimensionMember(**member_dict) for member_dict in members_data]

            print(f"\n  Target row/col: {target_rowcol}")
            print(f"  Members: {len(members)}")

            # Convert to dict for sending - serialize each step individually to preserve subclass fields
            analysis_request_dict = {
                "Pov": json.loads(pov.model_dump_json(by_alias=True)),
                "Members": [json.loads(m.model_dump_json(by_alias=True)) for m in members],
                "AnalysisSteps": [json.loads(step.model_dump_json(by_alias=True)) for step in steps],
            }

            print("\nAnalysis Request:")
            print(json.dumps(analysis_request_dict, indent=2))

            # Send the request
            print(f"\n{'='*80}")
            print(f"Sending Analysis Request to API for Artifact {idx}...")
            try:
                result = service.post_analysis(analysis_request_dict)
                print(f"\n✅ Analysis Response for Artifact {idx}:")
                print(json.dumps(result, indent=2))

                # Print members in hierarchical format with indentation
                if "Results" in result and result["Results"]:
                    print(f"\n📊 Hierarchical Member View:")
                    for member in result["Results"]:
                        indent = "  " * member.get("Level", 0)
                        member_name = member.get("MemberName", "")
                        print(f"{indent}{member_name}")
            except Exception as e:
                print(f"\n❌ Error sending analysis request for Artifact {idx}: {str(e)}")

        print(f"\n{'='*80}")
        print(f"✅ Completed processing all {len(artifacts)} artifact(s)!")


if __name__ == "__main__":
    asyncio.run(main())

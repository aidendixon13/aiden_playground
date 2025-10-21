"""
Scratch test file for DataAnalysisService
"""

import asyncio
import csv
import json
import os
import time
import difflib
from datetime import datetime

from regex import R

from wernicke.engines.processing.onestream_client.store.analysis_service import DataAnalysisService
from wernicke.agents.rubix.cube_view.subgraph_orchestrators.data_analysis_orchestrator.models import (
    POV,
    Analysis,
    AnalysisRequest,
    AnalysisType,
    BaseFilter,
    BaseSort,
    DimensionMember,
)

from wernicke.engines.auth.auth_manager import AuthManager


async def main():
    """
    Main function to test the DataAnalysisService.get_hello() method and load cube view artifacts.
    """
    # JWT token for authentication
    jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6IkJBRDgzOEZBRjI0MjUyQ0E2Q0YwMkJFMjA5QjQyQzY4IiwieDV0IjoidU1mUVk0WlhVQXZacUZkSTh6eFdaT0VhQkJnIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2xvY2FsaG9zdDo0NDM4NyIsIm5iZiI6MTc2MDY0MzQ2MCwiaWF0IjoxNzYwNjQzNDYwLCJleHAiOjE3NjA2NDcwNjAsImF1ZCI6ImFwaTovL3dlcm5pY2tlIiwic2NvcGUiOlsib3BlbmlkIiwiZW1haWwiLCJwcm9maWxlIiwiZ3JvdXBzIiwiYXBpOi8vd2Vybmlja2Uvd2Vybmlja2UuYWxsIiwib2ZmbGluZV9hY2Nlc3MiXSwiYW1yIjpbInB3ZCJdLCJjbGllbnRfaWQiOiJzZW5zaWJsZWdlbmFpLnBob2VuaXgiLCJzdWIiOiJlMjI1OWZmNC1iYTA2LTQ2NDEtOWIxMC1jMTNhYmU5ZGY4NWMiLCJhdXRoX3RpbWUiOjE3NjA2NDM0NTksImlkcCI6ImxvY2FsIiwiZ3JvdXAiOlsiQWRtaW5pc3RyYXRvcnMiLCJDX0Nsb3VkIiwiQ19DdXN0b21lciIsIkNfRmluUmVwb3J0aW5nIiwiQ19WZW5kb3IiLCJEX0FjY291bnRpbmciLCJEX0FkbWluIiwiRF9BSURlbGl2ZXJ5IiwiRF9BSURlbWFuZCIsIkRfQUlQcm9kRW5naW5lZXJpbmciLCJEX0FMTCIsIkRfQXJjaEZhY3RvcnkiLCJEX0FURyIsIkRfQnVzRGV2IiwiRF9CdXNEZXZfRU1FQSIsIkRfQnVzRGV2X05BIiwiRF9CdXNPcHMiLCJEX0Nsb3VkRGV2IiwiRF9DbG91ZE9wcyIsIkRfQ29tbWVyY2lhbFN0cmF0IiwiRF9Db25zdWx0U3ZjcyIsIkRfQ29uc3VsdFN2Y3NfRU1FQSIsIkRfQ29uc3VsdFN2Y3NfTkEiLCJEX0N1c3RTdWNjZXNzIiwiRF9DdXN0U3VwcG9ydCIsIkRfRERNa3RnIiwiRF9EZW1vRW5naW5lZXJpbmciLCJEX0VkdWNhdGlvblN2Y3MiLCJEX0VQTSIsIkRfRXZlbnRNZ210IiwiRF9GYWNpbGl0aWVzIiwiRF9GaW5hbmNlIiwiRF9IUiIsIkRfSW5mb1NlY3VyaXR5IiwiRF9JbmZvU3lzIiwiRF9JVCIsIkRfTGVnYWwiLCJEX01nbXQxIiwiRF9NZ210MTAiLCJEX01nbXQxMSIsIkRfTWdtdDEyIiwiRF9NZ210MTMiLCJEX01nbXQxNCIsIkRfTWdtdDIiLCJEX01nbXQzIiwiRF9NZ210NCIsIkRfTWdtdDUiLCJEX01nbXQ2IiwiRF9NZ210NyIsIkRfTWdtdDgiLCJEX01nbXQ5IiwiRF9Na3RQbGFjZURldiIsIkRfUEUiLCJEX1BFX0FQQUMiLCJEX1BFX0VNRUEiLCJEX1BFX05BIiwiRF9QbGF0RGV2IiwiRF9QbGF0Zm9ybUFyY2giLCJEX1ByZXNhbGVzIiwiRF9Qcm9kQ29tbSIsIkRfUHJvZEN1c3RFeHBNa3RnIiwiRF9Qcm9kTWdtdCIsIkRfUkMiLCJEX1Jpc2siLCJEX1NhbGVzIiwiRF9TYWxlc19BUEFDIiwiRF9TYWxlc19FTUVBIiwiRF9TYWxlc19OQSIsIkRfU2FsZXNFbmFibGUiLCJEX1NhbGVzT3BzIiwiRF9Tb2x1dGlvbk5ldHdvcmsiLCJEX1N0cmF0QWxsaWFuY2VzIiwiRF9TdHJhdENvbW1zIiwiREJfQnVzaW5lc3NQYXJ0bmVycyIsIkRCX0ZpbmFuY2UiLCJEcmlsbGl0X0FjY2VzcyIsIkVfQWxsX1JlYWQiLCJFX0FsbF9Xcml0ZSIsIkV2ZXJ5b25lIiwiRXZlcnlvbmVFeGNlcHRSZWFkT25seVVzZXJzIiwiSGVscF9IZWxwRGVza0VtYWlsIiwiT3Blbl9CYWNrdXBBcHAiLCJQb3dlclVzZXJzIiwiUl9DdWJlVmlld3MiLCJSX0RpbWVuc2lvbkxpYnJhcnkiLCJSX0ZYUmF0ZXMiLCJSX0pvdXJuYWxUZW1wbGF0ZXMiLCJSX1RhYmxlVmlld3MiLCJSX1RyYW5zUnVsZSIsIlJDTV9WaWV3IiwiU19BY3R1YWxfUmVhZCIsIlNfQWN0dWFsX1dyaXRlIiwiU19QbGFubmluZ19SZWFkIiwiU19QbGFubmluZ19Xcml0ZSIsIlNfU3RhdHV0b3J5X1JlYWQiLCJTX1N0YXR1dG9yeV9Xcml0ZSIsInN5c3RlbUFkbWlucyIsIlRNXzAxIiwiVE1fMDIiLCJUTV8wMyIsIlRNXzA0IiwiVE1fMDUiLCJUTV8wNiIsIlRNXzA3IiwiVE1fMDgiLCJUTV8wOSIsIlRNXzEwIiwiVE1fQWRtaW4iLCJUTV9Vc2VycyIsIlRvb2xLaXRfQWNjZXNzIl0sImV4dF9pYXQiOlsiMTc2MDY0MzQ2MCIsIjE3NjA2NDM0NjAiXSwicHJlZmVycmVkX3VzZXJuYW1lX29pcyI6IlRlc3QgVXNlciAxIiwic2NoZW1lX29pcyI6InhmbmF0aXZlIiwic2lkIjoiQkM0OUEwNkU4QTc1QzE1QzJFQUQwMTI0QUNDMkRBRkEiLCJqdGkiOiI2RjA3RkNCQ0U2QkIyRDRDQTNBOTI1QTEwOTA4QjlBRSJ9.k0EtONoHA7ylljrSn8GKZefIIB6Q1YlNdapGTL9ENt1IHkBoa_yo6u2VXyLGdlGsn2MM_-8gb8wJ7uv9QlJrOCf0Cpi5t3vNgHasef2Ct5hSFdRco2-UXr_0C3FUf2QJUuT4kHUhaGF8-mfjFzPNcm-fWHqEmF17WhQdh-cFwX4olpeV4xKQG2D-e8fbuRazlBOLLnArrjzjaGRGXdTlvQ0PwmxmxXvsda0Wwv28Ubktz1KMYrYxdDmLE4x67MuluYY90Y8uCEi5EzEiUE9W82Bib8b7DgLIfw9xCb__BiBWfe-Q4FI7rOhpBk0t-kG_V6aP-x1U5ns2RCNDeUDe5w"

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

    all_requests = []

    for artifact_dict in data["cube_view_artifacts"]:
        # Extract and remove analysis_steps, Members, and target_rowCol from artifact_data (they're not part of DynamicReportArtifact)
        artifact_data = artifact_dict["artifact_data"].copy()
        pov_data = artifact_data["pov"]
        pov = POV(**pov_data)
        analysis_data = artifact_data.pop("analysis")
        cube_view_analysis = []
        for analysis in analysis_data:
            row_cols = analysis["analysis_rowcol"]
            analysis_rowcols = []
            for row_col in row_cols:
                member = DimensionMember(**row_col)
                analysis_rowcols.append(member)

            analysis_steps_data = analysis["analysis_steps"]
            analysis_steps = []
            for step in analysis_steps_data:
                analysis_type = AnalysisType(step["AnalysisType"])
                if analysis_type == AnalysisType.SORT:
                    analysis_step = BaseSort(**step)
                elif analysis_type == AnalysisType.FILTER:
                    analysis_step = BaseFilter(**step)
                else:
                    raise ValueError(f"Unsupported AnalysisType: {analysis_type}")
                analysis_steps.append(analysis_step)
            analysis = Analysis(AnalysisRowCol=analysis_rowcols, AnalysisSteps=analysis_steps)
            cube_view_analysis.append(analysis)

        analysis_string = analysis.model_dump_json(indent=2, by_alias=True, exclude_none=True)
        pov_string = pov.model_dump_json(indent=2, by_alias=True, exclude_none=True)

        request = AnalysisRequest(Pov=pov, Analysis=cube_view_analysis)
        all_requests.append([request, artifact_dict["answer"]])

    print(f"\n{'='*80}")
    print(f"✅ Successfully loaded {len(all_requests)} cube view artifact(s)!")
    results = []
    total_score = 0
    for index, item in enumerate(all_requests):

        request_dict = item[0].model_dump(by_alias=True, exclude_none=True)

        try:
            start = time.perf_counter()
            result = service.post_analysis(request_dict)
            end = time.perf_counter()
            duration = end - start
            if item[1] == []:
                answers_filename = os.path.join(script_dir, f"answers_{index}.json")
                with open(answers_filename, "w") as f:
                    json.dump(result["Results"], f, indent=2)

            print(f"\n{'='*80}")
            print(f"{result['Results']}")
            print(f"{item[1]}")
            print(f"\n{'='*80}")
            print(f"{len(result['Results'])} results returned from analysis request in {round(duration, 4)} seconds")
            passed = result["Results"] == item[1]
            if passed:
                total_score += 1

            results.append({"index": index, "passed": passed, "duration_seconds": round(duration, 4), "timestamp": datetime.now().isoformat()})

        except Exception as e:
            print(f"\n❌ Error sending analysis request for Artifact {str(e)}")

    print(f"\n{'='*80}")
    print(f"Requests Processed {len(all_requests)}")
    print(f"\nFinal Score: {total_score / len(all_requests) * 100 }")
    print(f"\n{'='*80}")

    csv_file_path = os.path.join(script_dir, f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    with open(csv_file_path, "w", newline="") as csvfile:
        fieldnames = ["index", "passed", "duration_seconds", "timestamp", "error"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for result in results:
            writer.writerow(result)


if __name__ == "__main__":
    asyncio.run(main())

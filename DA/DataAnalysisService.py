"""
==============================================================================
Name: DataAnalysisService
Author:
Date: 10/13/2025
Description: Service for interacting with data analysis endpoints.
==============================================================================
"""

import json
from typing import Any, Dict

from pydantic import BaseModel

from wernicke.engines.processing.onestream_client.base import OneStreamServiceBase
from wernicke.engines.processing.onestream_client.models import StandardOSResponse
from wernicke.engines.processing.onestream_client.utils import create_service_config_from_user_session
from wernicke.internals.session.user_session import UserSessionInfo


class HelloResponse(BaseModel):
    """
    The response data that is returned from the hello endpoint.

    Attributes:
        message (str): The hello message returned from the endpoint.
    """

    message: str


class DataAnalysisService(OneStreamServiceBase):
    """
    The data analysis service allows us to reach out to OneStream for data analysis operations.
    """

    def __init__(self, user_session_info: UserSessionInfo):
        """
        Constructs the config for the OneStreamServiceBase from the user session info and initializes the client via the super.__init__

        Args:
            user_session_info (UserSessionInfo): The user's session information.
        """
        service_config = create_service_config_from_user_session(user_session_info=user_session_info)

        super().__init__(config=service_config)

    def get_hello(self) -> Dict[str, Any]:
        """
        This method calls the hello endpoint and returns the response data.

        Returns:
            Dict[str, Any]: The response data from the hello endpoint.

        Raises:
            RuntimeError: If the server returns a 500 error.
        """

        # Call hello GET endpoint
        get_resp = self._client.request(
            method="GET",
            url="api/v1/wernicke/hello",  # endpoint path
            headers={},
            params={},
        )

        print(get_resp.status_code)
        print(get_resp.reason)
        print(get_resp.content)

        # Check if the server returned a 500
        if get_resp.status_code == 500:
            # Handle the 500 error scenario
            raise RuntimeError(f"Error: {get_resp.status_code} {get_resp.reason}")

        # Parse the string content into a dict
        resp_json = json.loads(get_resp.content)

        # Then use Pydantic to validate
        resp = StandardOSResponse.model_validate(resp_json)
        return resp.data

    def post_analysis(self, analysis_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        This method sends an analysis request to the analysis endpoint.

        Args:
            analysis_request (Dict[str, Any]): The analysis request data containing POV, Members, and AnalysisSteps.

        Returns:
            Dict[str, Any]: The response data from the analysis endpoint.

        Raises:
            RuntimeError: If the server returns a 500 error.
        """

        # Call analysis POST endpoint
        post_resp = self._client.request(
            method="POST",
            url="api/v1/wernicke/analyze",  # endpoint path
            headers={"Content-Type": "application/json"},
            body=analysis_request,
        )

        print(f"POST Analysis Response: {post_resp.status_code}")
        print(post_resp.content)

        # Check if the server returned a 500
        if post_resp.status_code == 500:
            # Handle the 500 error scenario
            raise RuntimeError(f"Error: {post_resp.status_code} {post_resp.reason}")

        # Parse the string content into a dict
        resp_json = json.loads(post_resp.content)

        # Then use Pydantic to validate
        resp = StandardOSResponse.model_validate(resp_json)
        return resp.data

    def post_expand_rowcol(self, expand_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        This method sends a request to expand row/column members.

        Args:
            expand_request (Dict[str, Any]): The expand request data containing POV and RowCol member.

        Returns:
            Dict[str, Any]: The response data from the expand_rowcol endpoint.

        Raises:
            RuntimeError: If the server returns a 500 error.
        """

        # Call expand_rowcol POST endpoint
        post_resp = self._client.request(
            method="POST",
            url="api/v1/wernicke/expand_rowcol",  # endpoint path
            headers={"Content-Type": "application/json"},
            body=expand_request,
        )

        print(f"POST Expand RowCol Response: {post_resp.status_code}")
        print(post_resp.content)

        # Check if the server returned a 500
        if post_resp.status_code == 500:
            # Handle the 500 error scenario
            raise RuntimeError(f"Error: {post_resp.status_code} {post_resp.reason}")

        # Parse the string content into a dict
        resp_json = json.loads(post_resp.content)

        # Then use Pydantic to validate
        resp = StandardOSResponse.model_validate(resp_json)
        return resp.data

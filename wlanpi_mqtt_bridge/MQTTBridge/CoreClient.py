import logging
from typing import Optional, Any

import requests


class CoreClient:
    def __init__(
        self,
        base_url="http://127.0.0.1:31415",
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing CoreClient against {base_url}")
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
        self.openapi_def_path = f"{self.api_url}/openapi.json"

        self.base_headers = {
            "accept": "application/json",
            # "content-type": "application/x-www-form-urlencoded",
        }
        self.logger.info("CoreClient initialized")

    def get_openapi_definition(self) -> dict:
        self.logger.debug(f"Fetching OpenAPI definition from {self.openapi_def_path}")
        return requests.get(url=self.openapi_def_path, headers=self.base_headers).json()

    def execute_request(self, method: str, path: str, data:Optional[Any]=None, params:Optional[Any]=None):
        self.logger.debug(
            f"Executing {method.upper()} on path {path} with data: {str(data)}"
        )
        response = requests.request(
            method=method,
            params=params,
            url=f"{self.base_url}/{path}",
            json=data,
            headers=self.base_headers,
        )
        return response

    def get_current_path_data(self, path):
        self.logger.debug(f"Getting current path data for {path}")
        response =  self.execute_request('get', path)
        if response.status_code != 200:
            self.logger.error("Unable to get vlan data")
            return "ERROR"
        return response.json()

    def create_on_path(self, path, data):
        """ Probably not actually going to use this."""
        self.logger.info(f"Creating data on path {path}")
        target_url = f"{self.api_url}/{path}/create"
        self.logger.debug(f"Creating with URL {target_url} and data {data}")
        response = self.execute_request('post', path, data=data,)
        if response.status_code != 200:
            self.logger.error("Unable to successfully relay data")
            self.logger.error(f"Code: {response.status_code} Reason: {response.reason}")
            self.logger.error(response.raw)
            return "ERROR"
        return response.json()


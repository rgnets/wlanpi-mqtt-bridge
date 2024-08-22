import subprocess, requests, json
import logging

class CoreClient:
    def __init__(
            self,
            api_url='http://127.0.0.1:31415/api/v1',
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f'Initializing CoreClient against {api_url}')
        self.api_url = api_url
        self.openapi_def_path = f"{api_url}/openapi.json"

        self.base_headers = {
            "accept": "application/json",
            # "content-type": "application/x-www-form-urlencoded",
        }
        self.logger.info("CoreClient initialized")

    def get_openapi_definition(self):
        return requests.get(url = self.openapi_def_path, headers = self.base_headers).json()

    def get_current_path_data(self, path):
        self.logger.debug(f'Getting current path data for {path}')
        response = requests.get(
            f"{self.api_url}/{path}",
            params={},
            headers=self.base_headers,
        )
        if response.status_code != 200:
            self.logger.error("Unable to get vlan data")
            return 'ERROR'
        return response.json()

    def create_on_path(self, path, data):
        self.logger.info(f'Creating data on path {path}')
        target_url = f"{self.api_url}/{path}/create"
        self.logger.debug(f'Creating with URL {target_url} and data {data}')

        response = requests.post(
            target_url,
            json=data,
            headers=self.base_headers,
         )

        if response.status_code != 200:
            self.logger.error("Unable to successfully relay data")
            self.logger.error(f"Code: {response.status_code} Reason: {response.reason}")
            self.logger.error(response.raw)
            return 'ERROR'
        return response.json()

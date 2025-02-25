import json
import logging
import pprint

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


class ApstraClient:
    def __init__(self, base_url, username, port, password, ssl_verify):
        self.auth_token = None
        self.base_url = base_url
        self.username = username
        self.password = password
        self.port = port
        self.ssl_verify = ssl_verify
        self.login()

    def login(self):
        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}:{self.port}/api/aaa/login",
                json={
                    "username": self.username,
                    "password": self.password
                },
                verify=self.ssl_verify
            )
            response.raise_for_status()
            self.auth_token = response.json().get('token')
            #breakpoint()
            if not self.auth_token:
                logger.exception("No token in authentication response")
                return
            logger.info("Successfully obtained authentication token")
            return
        except Exception as e:
            logger.exception(f"Failed to get auth token: {str(e)}")
            return

    def make_api_request(self, method, endpoint, data=None):
        try:
            url = f"{self.base_url.rstrip('/')}:{self.port}{endpoint}"
            headers = {'authtoken': self.auth_token}
            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                verify=self.ssl_verify
            )

            if response.status_code == 401:
                self.login()
                if self.auth_token:
                    headers = {'authtoken': self.auth_token}
                    response = requests.request(
                        method=method,
                        url=url,
                        data=data,
                        headers=headers,
                        verify=self.ssl_verify
                    )
            response.raise_for_status()
            if response.text.strip()=="":
                return {}
            else:
                return response.json()
        except Exception as e:
            logger.exception(f"API request failed: {str(e)}")
            raise

    def get_task_details(self, blueprint_id, task_id):
        """Get detailed task info"""
        try:
            endpoint = f"/api/blueprints/{blueprint_id}/tasks/{task_id}"
            logger.debug(f"Getting task details for task {task_id}")
            task_detail = self.make_api_request('GET', endpoint)
            if not task_detail:
                logger.error(f"No details returned for task {task_id}")
                return None
            return task_detail
        except Exception as e:
            logger.error(f"Failed to get task details for {task_id}: {str(e)}")
            return None

    def get_tasks(self, blueprint_id):
        """Get detailed task info"""
        try:
            endpoint = f"/api/blueprints/{blueprint_id}/tasks"
            logger.debug(f"Polling tasks with endpoint: {endpoint}")

            response = self.make_api_request('GET', endpoint)
            if not response:
                logger.error("Received empty response from API")
                return []
            return response.get('items', [])
        except Exception as e:
            logger.exception(e)

    def get_anomalies(self, blueprint_id):
        try:
            endpoint = f"/api/blueprints/{blueprint_id}/anomalies"
            logger.debug(f"Polling tasks with endpoint: {endpoint}")

            response = self.make_api_request('GET', endpoint)
            if not response:
                logger.error("Received empty response from API")
                return []
            return response.get('items', [])
        except Exception as e:
            logger.exception(e)

    def get_bp_ids(self):
        try:
            endpoint = f"/api/blueprints"
            logger.debug(f"Get Blueprints with endpoint: {endpoint}")

            response = self.make_api_request('GET', endpoint)
            if not response:
                logger.error("Received empty response from API")
                return []
            return response.get('items', [])
        except Exception as e:
            logger.exception(e)

    def get_bp(self, bp_id):
        try:
            endpoint = f"/api/blueprints/{bp_id}"
            logger.debug(f"Get Blueprint with id: {bp_id}")

            return self.make_api_request('GET', endpoint)

        except Exception as e:
            logger.exception(e)

    def get_property_set(self, name):
        try:
            endpoint = f"/api/property-sets"
            ps = self.make_api_request('GET', endpoint)['items']
            #breakpoint()
            #print(ps)
            for p in ps:
                if p['label'] == name:
                    return p
            raise Exception("Property Set Not Found")
        except Exception as e:
            logger.exception(e)
            raise

    def make_property_set(self, p):
        ep = f"/api/property-sets"
        try:
            self.make_api_request(method='POST', endpoint=ep, data=p)
        except Exception as e:
            logger.exception(e)
            raise
        return self.get_property_set(p['label'])

    def update_property_set(self, ps_id, p):
        ep = f"/api/property-sets/{ps_id}"
        try:
            self.make_api_request(method='PUT', endpoint=ep, data=p)
        except Exception as e:
            logger.exception(e)
            raise
import os
import time
import json
import logging
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

def create_apstra_client(config):
    """
    Creates an Apstra API client
    """
    auth_token = None
    last_request_time = 0
    min_request_interval = config.get('min_request_interval', 0.5)
    max_retries = config.get('max_retries', 3)
    ssl_verify = config.get('ssl_verify', False)
    
    def get_auth_token():
        try:
            response = requests.post(
                f"{config['base_url'].rstrip('/')}/api/aaa/login",
                json={
                    "username": config['username'],
                    "password": config['password']
                },
                verify=ssl_verify
            )
            response.raise_for_status()
            token = response.json().get('token')
            if not token:
                logger.error("No token in authentication response")
                return None
            logger.info("Successfully obtained authentication token")
            return token
        except Exception as e:
            logger.error(f"Failed to get auth token: {str(e)}")
            return None

    def make_api_request(method, endpoint, data=None):
        nonlocal auth_token
        try:
            if not auth_token:
                auth_token = get_auth_token()
                if not auth_token:
                    logger.error("Failed to get authentication token")
                    return None

            url = f"{config['base_url'].rstrip('/')}{endpoint}"
            headers = {'authtoken': auth_token}
            
            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                verify=ssl_verify
            )
            
            if response.status_code == 401:
                auth_token = get_auth_token()
                if auth_token:
                    headers = {'authtoken': auth_token}
                    response = requests.request(
                        method=method,
                        url=url,
                        json=data,
                        headers=headers,
                        verify=ssl_verify
                    )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return None

    # Initialize authentication
    auth_token = get_auth_token()
    if not auth_token:
        logger.error("Failed to initialize API client - could not get authentication token")
        return None

    return {
        'make_api_request': make_api_request
    }
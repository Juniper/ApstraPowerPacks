#!/usr/bin/env python3

from src.poller import ApstraClient
import os
from dotenv import load_dotenv
import json
from datetime import datetime

def main():
    # Load config
    load_dotenv('config/.env')
    
    # Create client
    client = ApstraClient(
        base_url=os.getenv('APSTRA_API_URL'),
        username=os.getenv('APSTRA_USERNAME'),
        password=os.getenv('APSTRA_PASSWORD'),
        verify_ssl=False
    )
    
    # Test connection
    if not client.login():
        print("Failed to connect to Apstra")
        return
    
    # Get tasks
    tasks = client.get_tasks(os.getenv('APSTRA_BLUEPRINT_ID'))
    print(f"Found {len(tasks)} tasks")
    
    if tasks:
        print("\nLatest task:")
        latest = tasks[0]
        print(json.dumps(latest, indent=2))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3

from src.poller import ApstraClient
import os
from dotenv import load_dotenv
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)

def parse_timestamp(ts_str: str) -> float:
    return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()

def format_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

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
    
    if not client.login():
        print("Failed to connect to Apstra")
        return
    
    # Get tasks
    tasks = client.get_tasks(os.getenv('APSTRA_BLUEPRINT_ID'))
    print(f"\nFound {len(tasks)} tasks")
    
    if tasks:
        # Print task timeline
        print("\nTask Timeline:")
        print("=" * 80)
        for task in tasks:
            ts = task['_timestamp']
            print(f"\nTimestamp: {format_timestamp(ts)}")
            print(f"Task ID: {task['id']}")
            print(f"Type: {task['type']}")
            print(f"Status: {task.get('status', 'N/A')}")
            print(f"User: {task['user_name']}")
            print("-" * 80)
            
        # Verify ordering
        timestamps = [task['_timestamp'] for task in tasks]
        is_ordered = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
        print("\nTimestamp Analysis:")
        print(f"Oldest task: {format_timestamp(timestamps[0])}")
        print(f"Newest task: {format_timestamp(timestamps[-1])}")
        print(f"Tasks are in chronological order: {is_ordered}")
        
        # Show time range
        time_range = timestamps[-1] - timestamps[0]
        print(f"Time range covered: {time_range/3600:.2f} hours")
        
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from src.storage.redis_client import AuditStorage
from src.poller.apstra_client import ApstraClient
from datetime import datetime
import os
from dotenv import load_dotenv
import json

def test_apstra_connection():
    """Test Apstra API connection"""
    print("\n1. Testing Apstra API Connection...")
    
    # Load environment variables
    load_dotenv('config/.env')
    
    client = ApstraClient(
        base_url=os.getenv('APSTRA_API_URL'),
        username=os.getenv('APSTRA_USERNAME'),
        password=os.getenv('APSTRA_PASSWORD'),
        verify_ssl=False
    )
    
    if client.login():
        print("✅ Successfully connected to Apstra API")
        
        # Test getting tasks
        tasks = client.get_tasks(os.getenv('APSTRA_BLUEPRINT_ID'))
        if tasks:
            print(f"✅ Successfully retrieved {len(tasks)} tasks")
            print("\nSample task:")
            print(json.dumps(tasks[0], indent=2))
        else:
            print("❌ No tasks retrieved")
    else:
        print("❌ Failed to connect to Apstra API")

def test_storage():
    """Test Redis storage"""
    print("\n2. Testing Redis Storage...")
    
    storage = AuditStorage()
    latest_events = storage.get_latest_events(5)
    
    if latest_events:
        print(f"✅ Found {len(latest_events)} events in storage")
        print("\nMost recent events:")
        for event in latest_events:
            print(f"\nTimestamp: {datetime.fromtimestamp(event.timestamp)}")
            print(f"User: {event.user}")
            print(f"Action: {event.action}")
            print(f"Details: {json.dumps(event.details, indent=2)}")
    else:
        print("ℹ️  No events found in storage")

if __name__ == "__main__":
    test_apstra_connection()
    test_storage()

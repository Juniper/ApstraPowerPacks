#!/usr/bin/env python3
from src.storage.redis_client import AuditStorage
from src.storage.models import AuditEvent
from datetime import datetime

def test_storage():
    print("\nTesting storage system...")
    try:
        # Create storage instance
        storage = AuditStorage()
        
        # Create test event
        test_event = AuditEvent.create(
            user="test_user",
            action="test_action",
            details={"test": "data", "timestamp": datetime.now().isoformat()}
        )
        
        # Store event
        if not storage.add_event(test_event):
            raise Exception("Failed to store event")
        print("✅ Stored test event successfully")
        
        # Retrieve events
        events = storage.get_latest_events(1)
        if not events:
            raise Exception("Failed to retrieve events")
            
        print("\nRetrieved test event:")
        print(f"User: {events[0].user}")
        print(f"Action: {events[0].action}")
        print(f"Details: {events[0].details}")
        print("✅ Retrieved test event successfully")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_storage()

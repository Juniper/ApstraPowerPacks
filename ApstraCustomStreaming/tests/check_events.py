#!/usr/bin/env python3

from src.storage.redis_client import AuditStorage
from datetime import datetime

def format_timestamp(ts):
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def main():
    storage = AuditStorage()
    
    # Get total count
    total = storage.get_total_events()
    print(f"\nTotal events stored: {total}")
    
    # Get latest events
    print("\nLatest 5 events:")
    print("-" * 80)
    
    events = storage.get_latest_events(5)
    for event in events:
        print(f"Time: {format_timestamp(event.timestamp)}")
        print(f"User: {event.user}")
        print(f"Action: {event.action}")
        print(f"Status: {event.details.get('status')}")
        print("-" * 80)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3

from src.storage.redis_client import AuditStorage
from datetime import datetime
import json

def format_timestamp(ts):
    try:
        return datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return ts

def show_redis_data():
    storage = AuditStorage()
    
    print("\n=== Redis Data Structure Overview ===")
    
    # Show all keys
    all_keys = storage.redis.keys('*')
    print(f"\nTotal Redis Keys: {len(all_keys)}")
    print("Keys found:", all_keys)
    
    # Show Redis memory usage
    info = storage.redis.info(section="memory")
    print("\n=== Redis Memory Usage ===")
    print(f"Used Memory: {info.get('used_memory_human', 'N/A')}")
    print(f"Peak Memory: {info.get('used_memory_peak_human', 'N/A')}")
    
    # Get all events with scores and sort by timestamp
    print("\n=== Audit Events (Oldest to Newest) ===")
    events = storage.redis.zrange('audit_events', 0, -1, withscores=True)
    print(f"Total events stored: {len(events)}")
    print("\nEvents:")
    print("=" * 80)
    
    # Convert to list and sort by timestamp
    event_list = []
    for event_id, score in events:
        event_data = storage.redis.hgetall(f"audit_details:{event_id}")
        if event_data:
            event_list.append((score, event_id, event_data))
    
    # Sort by timestamp
    event_list.sort(key=lambda x: x[0])
    
    # Print events
    for score, event_id, event_data in event_list:
        print(f"\nTimestamp: {format_timestamp(score)}")
        print(f"Event ID: {event_id}")
        print(f"User: {event_data.get('user', 'N/A')}")
        print(f"Action: {event_data.get('action', 'N/A')}")
        try:
            details = json.loads(event_data.get('details', '{}'))
            print("Details:")
            print(f"  Status: {details.get('status', 'N/A')}")
            print(f"  User IP: {details.get('user_ip', 'N/A')}")
            if 'request_data' in details:
                request = details['request_data']
                print(f"  Request URL: {request.get('url', 'N/A')}")
                print(f"  Request Method: {request.get('method', 'N/A')}")
        except json.JSONDecodeError:
            print(f"Raw Details: {event_data.get('details', 'N/A')}")
        print("-" * 80)
    
    if event_list:
        print(f"\nOldest event: {format_timestamp(event_list[0][0])}")
        print(f"Newest event: {format_timestamp(event_list[-1][0])}")
    print("\n" + "=" * 80)

def main():
    try:
        show_redis_data()
    except Exception as e:
        print(f"Error accessing Redis: {str(e)}")
        print("Make sure Redis is running:")
        print("  brew services start redis")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3

from src.storage.redis_client import AuditStorage
from datetime import datetime
import time
import os
import sys
import json

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def format_timestamp(ts):
    return datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S')

def format_json(data):
    """Format JSON data with proper indentation"""
    try:
        return json.dumps(data, indent=2)
    except:
        return str(data)

def show_latest_record():
    """Show complete information for the most recent record"""
    storage = AuditStorage()
    events = storage.get_latest_events(1)
    
    if not events:
        return "No events found in storage"
        
    event = events[0]
    
    # Format the complete record
    record = [
        "=== Latest Record ===",
        f"Timestamp: {format_timestamp(event.timestamp)}",
        f"Event ID: {event.event_id}",
        f"User: {event.user}",
        f"Action: {event.action}",
        "\nComplete Details:",
        format_json(event.details),
        "=" * 80
    ]
    
    return "\n".join(record)

def monitor_service():
    storage = AuditStorage()
    last_count = 0
    start_time = datetime.now()

    try:
        while True:
            clear_screen()
            print("\n=== Apstra Task Audit Service Monitor ===")
            print(f"Running since: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Get current count
            current_count = storage.get_total_events()
            
            # Show counts
            print(f"\nTotal events in storage: {current_count}")
            if current_count > last_count:
                print(f"New events since last check: {current_count - last_count}")
            
            # Show latest record
            print("\n" + show_latest_record())
            
            # Update last count
            last_count = current_count

            # Show instructions
            print("\nPress Ctrl+C to exit")
            print("Refreshing in 5 seconds...")
            time.sleep(5)

    except KeyboardInterrupt:
        print("\nMonitor stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    monitor_service()

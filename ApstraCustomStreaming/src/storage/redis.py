import json
import redis

def create_redis_connection(redis_host='localhost', redis_port=6379, max_entries=1500):
    print(redis_port)
    return redis.Redis(host=redis_host, port=redis_port,  decode_responses=True)

def add_event(redis_conn, event_id, user, action, details, timestamp, max_entries=1500):
    """
    Add a new audit event, maintaining the maximum entry limit.
    Returns True if successful, False if failed.
    """
    events_key = 'audit_events'  # Sorted set for timestamps
    details_key = 'audit_details'  # Hash for event details
    
    try:
        # Create pipeline for atomic operation
        pipe = redis_conn.pipeline()
        
        # Store event details in hash
        event_data = {
            'user': user,
            'action': action,
            'details': json.dumps(details),
            'timestamp': timestamp
        }
        pipe.hset(f"{details_key}:{event_id}", mapping=event_data)
        
        # Add to sorted set with timestamp as score
        pipe.zadd(events_key, {event_id: timestamp})

        # Publish event to the Redis channel
        redis_conn.publish('new_event_channel', json.dumps(event_data))
        
        # Trim to max entries if needed
        current_size = pipe.zcard(events_key)
        if current_size.execute()[0] >= max_entries:
            # Get oldest entries that need to be removed
            to_remove = pipe.zrange(events_key, 0, current_size - max_entries)
            if to_remove.execute()[0]:
                # Remove from sorted set and delete their details
                pipe.zremrangebyrank(events_key, 0, len(to_remove) - 1)
                for old_id in to_remove:
                    pipe.delete(f"{details_key}:{old_id}")
        
        pipe.execute()
        return True
        
    except redis.RedisError as e:
        print(f"Redis error: {e}")
        return False

def get_events_since(redis_conn, timestamp):
    """
    Retrieve all events since given timestamp.
    """
    events_key = 'audit_events'
    details_key = 'audit_details'
    
    try:
        # Get all event IDs since timestamp
        event_ids = redis_conn.zrangebyscore(events_key, timestamp, '+inf')
        
        events = []
        for event_id in event_ids:
            event_data = redis_conn.hgetall(f"{details_key}:{event_id}")
            if event_data:
                event_data['timestamp'] = float(event_data['timestamp'])
                event_data['details'] = json.loads(event_data['details'])
                event_data['event_id'] = event_id
                events.append(event_data)
        
        return events
        
    except redis.RedisError as e:
        print(f"Redis error: {e}")
        return []

def get_latest_events(redis_conn, limit=100):
    """
    Get the most recent events, up to specified limit.
    """
    events_key = 'audit_events'
    details_key = 'audit_details'
    
    try:
        # Get the most recent event IDs
        event_ids = redis_conn.zrevrange(events_key, 0, limit - 1)
        
        events = []
        for event_id in event_ids:
            event_data = redis_conn.hgetall(f"{details_key}:{event_id}")
            if event_data:
                event_data['timestamp'] = float(event_data['timestamp'])
                event_data['details'] = json.loads(event_data['details'])
                event_data['event_id'] = event_id
                events.append(event_data)
        
        return events
        
    except redis.RedisError as e:
        print(f"Redis error: {e}")
        return []

def get_total_events(redis_conn):
    """
    Get total number of events currently stored.
    """
    try:
        return redis_conn.zcard('audit_events')
    except redis.RedisError:
        return 0
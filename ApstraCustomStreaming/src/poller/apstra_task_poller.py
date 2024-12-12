# src/poller/apstra_task_poller.py

import time
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def create_task_poller(api_client, storage_client, config):
    """
    Task-specific poller using the base Apstra client
    
    Args:
        api_client (dict): Base Apstra API client functions
        storage_client: Redis client
        config (dict): Poll interval, blueprint ID, max entries
    """
    last_poll_time = None
    running = False

    def get_task_details(task_id, blueprint_id):
        """Get detailed task info"""
        try:
            endpoint = f"/api/blueprints/{blueprint_id}/tasks/{task_id}"
            logger.debug(f"Getting task details for task {task_id}")
            task_detail = api_client['make_api_request']('GET', endpoint)
            if not task_detail:
                logger.error(f"No details returned for task {task_id}")
                return None
            return task_detail
        except Exception as e:
            logger.error(f"Failed to get task details for {task_id}: {str(e)}")
            return None

    def store_event(event):
        """Store event in Redis with FIFO handling"""
        try:
            current_count = storage_client.llen('apstra_events')
            if current_count >= config.get('max_entries', 1500):
                logger.debug("Max entries reached, removing oldest event")
                storage_client.rpop('apstra_events')
            
            storage_client.lpush('apstra_events', json.dumps(event))
            return True
        except Exception as e:
            logger.error(f"Failed to store event in Redis: {str(e)}")
            return False

    def poll_once():
        """Single poll iteration"""
        nonlocal last_poll_time
        try:
            endpoint = f"/api/blueprints/{config['blueprint_id']}/tasks"
            logger.debug(f"Polling tasks with endpoint: {endpoint}")
            
            response = api_client['make_api_request']('GET', endpoint)
            if not response:
                logger.error("Received empty response from API")
                return 0
                
            tasks = response.get('items', [])
            logger.debug(f"Retrieved {len(tasks)} tasks")
            
            count = 0
            for task in tasks:
                try:
                    created_ts = datetime.strptime(
                        task['created_at'], 
                        "%Y-%m-%dT%H:%M:%S.%fZ"
                    ).timestamp()
                    
                    if last_poll_time is None or created_ts > last_poll_time:
                        task_detail = get_task_details(task['id'], config['blueprint_id'])
                        if not task_detail:
                            continue
                        
                        event = {
                            'timestamp': created_ts,
                            'user': task_detail.get('user_name'),
                            'action': task_detail.get('type'),
                            'details': task_detail,
                            'event_id': task_detail.get('id')
                        }
                        
                        if store_event(event):
                            count += 1
                            logger.debug(f"Stored event for task {task['id']}")
                
                except (KeyError, ValueError) as e:
                    logger.error(f"Error processing task {task.get('id', 'unknown')}: {str(e)}")
                    continue
            
            if tasks:
                last_poll_time = max(
                    datetime.strptime(task['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp() 
                    for task in tasks
                )
                logger.debug(f"Updated last poll time to: {last_poll_time}")
            
            return count
            
        except Exception as e:
            logger.error(f"Error during polling: {str(e)}", exc_info=True)
            return 0

    def start_polling():
        """Start continuous polling process"""
        nonlocal running
        running = True
        
        logger.info(f"Starting task polling with interval {config.get('poll_interval', 60)} seconds...")
        while running:
            try:
                new_events = poll_once()
                if new_events > 0:
                    logger.info(f"Poll complete - Processed {new_events} new events")
                else:
                    logger.debug("Poll complete - No new events")
                
                if running:
                    time.sleep(config.get('poll_interval', 60))
                    
            except Exception as e:
                logger.error(f"Polling error: {str(e)}", exc_info=True)
                if running:
                    logger.info(f"Waiting {config.get('poll_interval', 60)} seconds before retry...")
                    time.sleep(config.get('poll_interval', 60))
    
    def stop_polling():
        """Gracefully stop polling"""
        nonlocal running
        running = False
        logger.info("Stopping task polling...")
    
    return {
        'start_polling': start_polling,
        'stop_polling': stop_polling
    }
# src/outputs/streaming_to_webhooks.py

import redis
import json
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def stream_to_webhook(config):
    """
    Stream events from Redis to webhook endpoint.
    """
    # Redis setup
    redis_client = redis.Redis(
        host=config['redis']['host'],
        port=config['redis']['port'],
        decode_responses=True
    )
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe(config['redis']['channel'])
    
    # Webhook setup
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Apstra-Webhook-Forwarder/1.0'
    }
    
    if 'auth_token' in config:
        headers['Authorization'] = f"Bearer {config['auth_token']}"

    logger.info(f"Starting webhook streaming to: {config['webhook_url']}")
    logger.info(f"Subscribed to Redis channel: {config['redis']['channel']}")

    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    event_data = json.loads(message['data'])
                    
                    # Format payload
                    payload = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "event_type": "apstra_task",
                        "data": event_data,
                        "metadata": {
                            "source": "apstra_task_monitor",
                            "version": "1.0"
                        }
                    }

                    # Send to webhook
                    response = requests.post(
                        config['webhook_url'],
                        json=payload,
                        headers=headers,
                        timeout=config.get('timeout', 10)
                    )
                    response.raise_for_status()
                    logger.info(f"Successfully sent webhook. Status: {response.status_code}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Redis message: {e}")
                except requests.exceptions.RequestException as e:
                    logger.error(f"Failed to send webhook: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}", exc_info=True)
                    
    except KeyboardInterrupt:
        logger.info("Shutting down webhook streaming...")
    finally:
        pubsub.unsubscribe()
        redis_client.close()

if __name__ == "__main__":
    # For testing directly
    import yaml
    
    with open("config/default_config.yml", "r") as f:
        config = yaml.safe_load(f)
        
    stream_to_webhook(config['outputs']['webhook'])
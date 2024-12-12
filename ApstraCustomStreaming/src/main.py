# main.py
import os
import sys
import logging
import time
import threading
from config.config_manager import (
    load_config,
    get_redis_config,
    get_output_config,
    get_apstra_api_config
)
from src.storage import redis
from src.poller.apstra_client_api_poller import create_apstra_client
from src.poller.apstra_task_poller import create_task_poller

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True
)

logger = logging.getLogger(__name__)

# def start_output_handlers(configs, storage):
#     """Start enabled output handlers in separate threads."""
#     threads = []
    
#     # Start syslog output if enabled
#     syslog_config = get_output_config('syslog', configs)
#     if syslog_config.get('enabled'):
#         logger.info("Starting syslog output...")
#         syslog_thread = threading.Thread(
#             target=start_syslog_streaming,
#             args=(syslog_config,),
#             name="SyslogOutput",
#             daemon=True
#         )
#         threads.append(syslog_thread)
#         syslog_thread.start()

#     # Start webhook output if enabled
#     webhook_config = get_output_config('webhook', configs)
#     if webhook_config.get('enabled'):
#         logger.info("Starting webhook output...")
#         webhook_thread = threading.Thread(
#             target=stream_to_webhook,
#             args=(webhook_config,),
#             name="WebhookOutput",
#             daemon=True
#         )
#         threads.append(webhook_thread)
#         webhook_thread.start()
    
#     return threads

def run_polling_loop(poller, poll_interval):
    """Run the main polling loop."""
    logger.info(f"Starting polling loop with {poll_interval} second interval...")
    
    while True:
        try:
            logger.debug("Starting poll iteration...")
            new_events = poller.poll_once()
            logger.info(f"Poll complete - Found {new_events} new events")
            
            logger.debug(f"Sleeping for {poll_interval} seconds...")
            time.sleep(poll_interval)
            
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            break
        except Exception as e:
            logger.error(f"Error during polling: {str(e)}", exc_info=True)
            logger.info("Waiting before retry...")
            time.sleep(poll_interval)

def main():
    try:
        logger.info("Starting Apstra Task Audit Trail Service")
        
        # Load all configurations
        configs = load_config()
        logger.info("Configuration loaded successfully")

        # Initialize storage
        redis_config = get_redis_config(configs)
        storage = redis.create_redis_connection(
            redis_host=redis_config.get('host', 'localhost'),
            redis_port=redis_config.get('port', 6379),
            max_entries=redis_config.get('max_entries', 1500)
        )
        logger.info("Storage initialized")

        # # Start enabled outputs
        # output_threads = start_output_handlers(configs, storage)
        # logger.info(f"Started {len(output_threads)} output handlers")

        # Initialize Apstra client
        api_config = get_apstra_api_config(configs)
        api_client = create_apstra_client(api_config)
        
        if not api_client:
            logger.error("Failed to create API client")
            return

        # Create task poller
        poller = create_task_poller(
            api_client=api_client,
            storage_client=storage,
            config={
                'poll_interval': api_config.get('poll_interval', 60),
                'blueprint_id': api_config['blueprint_id'],
                'max_entries': redis_config.get('max_entries', 1500)
            }
        )

        try:
            logger.info("Starting polling process...")
            poller['start_polling']()
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            if 'poller' in locals():
                poller['stop_polling']()
        except Exception as e:
            logger.error(f"Error in polling process: {str(e)}", exc_info=True)
        finally:
            logger.info("Shutting down service...")
                
    except Exception as e:
        logger.error(f"Service error: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Shutting down service...")

if __name__ == "__main__":
    main()



# # TODO

# output -> syslog

# - turn from class to script
# - remove typing
# - understand what script is doing
# - update main to work with syslog


# output -> webhooks

# - turn from class to script
# - remove typing
# - understand what script is doing
# - update main to work with webhooks

# poller -> apstra_polling

# - turn from class to script
# - remove typing
# - understand what script is doing
# - update main to work with webhooks
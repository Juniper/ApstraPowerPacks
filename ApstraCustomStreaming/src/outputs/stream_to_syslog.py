import redis
import json
import logging
import socket
import os
from typing import Optional
from syslog_rfc5424_formatter import RFC5424Formatter
from logging.handlers import SysLogHandler

class SyslogOutput:
    """Handles streaming events to syslog server using RFC5424 format."""
    
    def __init__(self, config: dict):
        """
        Initialize the SyslogOutput with configuration.
        
        Args:
            config (dict): Configuration dictionary containing syslog and redis settings
        """
        self.config = config
        self.logger: Optional[logging.Logger] = None
        self.redis_client: Optional[redis.Redis] = None
        self._setup_logger()
        self._setup_redis()

    def _setup_logger(self) -> None:
        """Configure syslog logger with RFC5424 formatting."""
        self.logger = logging.getLogger('ApstraTaskAudit')
        self.logger.setLevel(logging.INFO)

        # Get syslog configuration
        syslog_config = self.config.get('syslog', {})
        server = syslog_config.get('server', 'localhost')
        port = syslog_config.get('port', 514)
        protocol = syslog_config.get('protocol', 'udp')
        
        # Get facility
        facility_name = syslog_config.get('facility', 'local0').upper()
        facility = getattr(SysLogHandler, facility_name, SysLogHandler.LOG_LOCAL0)

        # Use socket constants for protocol type
        sock_type = socket.SOCK_DGRAM if protocol.lower() == 'udp' else socket.SOCK_STREAM
        
        try:
            # Create syslog handler
            syslog_handler = SysLogHandler(
                address=(server, port),
                socktype=sock_type,
                facility=facility
            )
            
            # Configure RFC5424 formatter
            # Using only the supported parameters
            formatter = RFC5424Formatter()
            
            syslog_handler.setFormatter(formatter)
            self.logger.addHandler(syslog_handler)
            
            self.logger.info("Syslog handler configured successfully")
        except Exception as e:
            logging.error(f"Failed to setup syslog handler: {str(e)}")
            raise

    def _setup_redis(self) -> None:
        """Configure Redis client for event subscription."""
        redis_config = self.config.get('redis', {})
        try:
            self.redis_client = redis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
        except redis.ConnectionError as e:
            logging.error(f"Failed to connect to Redis: {str(e)}")
            raise

    def _format_event_message(self, event_data: dict) -> str:
        """
        Format the complete event data into a structured message.
        
        Args:
            event_data (dict): The complete event data from Redis
            
        Returns:
            str: Formatted message string containing all event data
        """
        try:
            # Create a list of key-value pairs from the event data
            event_details = []
            
            # Process top-level fields
            for key, value in event_data.items():
                if isinstance(value, (dict, list)):
                    # Convert complex objects to JSON string
                    event_details.append(f"{key}={json.dumps(value)}")
                else:
                    # Handle simple values
                    event_details.append(f"{key}={value}")
            
            # Join all details with a separator
            message = " | ".join(event_details)
            
            # Add a prefix to clearly identify the message
            return f"ApstraTaskAudit: {message}"
            
        except Exception as e:
            logging.warning(f"Error formatting message: {str(e)}. Using raw data.")
            return f"ApstraTaskAudit: RAW_DATA | {str(event_data)}"

    def start(self) -> None:
        """Start listening for events and forwarding to syslog."""
        if not self.logger or not self.redis_client:
            raise RuntimeError("Syslog output not properly initialized")

        redis_config = self.config.get('redis', {})
        channel = redis_config.get('channel', 'new_event_channel')
        
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channel)

        self.logger.info(f"Starting syslog output, listening on channel: {channel}")
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # Parse the Redis message
                        event_data = json.loads(message['data'])
                        
                        # Format the complete event data
                        formatted_message = self._format_event_message(event_data)
                        
                        # Log the message
                        self.logger.info(formatted_message)
                        
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON message received: {message['data']}")
                    except Exception as e:
                        self.logger.error(f"Error processing message: {str(e)}")
                        continue
                        
        except KeyboardInterrupt:
            self.logger.info("Syslog output stopped by user")
        except Exception as e:
            self.logger.error(f"Syslog output error: {str(e)}")
            raise
        finally:
            if pubsub:
                pubsub.unsubscribe()

    def stop(self) -> None:
        """Stop the syslog output and cleanup resources."""
        if self.redis_client:
            try:
                self.redis_client.close()
                self.logger.info("Syslog output stopped")
            except Exception as e:
                self.logger.error(f"Error during shutdown: {str(e)}")
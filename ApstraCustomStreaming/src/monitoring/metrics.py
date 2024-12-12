from datetime import datetime, timedelta
import threading
import logging
from typing import Dict, List, Tuple
import time

class EventMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()
        
    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self._event_counts = []  # List of (timestamp, count) tuples
            self._total_events = 0
            self._failed_polls = 0
            self._last_successful_poll = None
            self._last_error = None
            
    def add_events(self, count: int):
        """Record new events"""
        with self._lock:
            self._event_counts.append((datetime.now(), count))
            self._total_events += count
            self._last_successful_poll = datetime.now()
            
            # Clean up old metrics (keep last hour)
            cutoff = datetime.now() - timedelta(hours=1)
            self._event_counts = [(ts, cnt) for ts, cnt in self._event_counts if ts > cutoff]
    
    def record_error(self, error: str):
        """Record a polling error"""
        with self._lock:
            self._failed_polls += 1
            self._last_error = error
            
    def get_events_per_minute(self) -> float:
        """Calculate events per minute over the last 5 minutes"""
        with self._lock:
            now = datetime.now()
            five_min_ago = now - timedelta(minutes=5)
            
            # Filter events in last 5 minutes
            recent_events = [(ts, cnt) for ts, cnt in self._event_counts if ts > five_min_ago]
            
            if not recent_events:
                return 0.0
                
            total_count = sum(count for _, count in recent_events)
            elapsed_minutes = (now - min(ts for ts, _ in recent_events)).total_seconds() / 60
            
            return total_count / max(elapsed_minutes, 1)  # Avoid division by zero
            
    def get_metrics_report(self) -> Dict:
        """Get comprehensive metrics report"""
        with self._lock:
            now = datetime.now()
            
            return {
                'events_per_minute': self.get_events_per_minute(),
                'total_events': self._total_events,
                'failed_polls': self._failed_polls,
                'last_successful_poll': (
                    (now - self._last_successful_poll).total_seconds() 
                    if self._last_successful_poll else None
                ),
                'last_error': self._last_error,
                'recent_counts': [
                    {
                        'timestamp': ts.isoformat(),
                        'count': cnt
                    }
                    for ts, cnt in sorted(self._event_counts[-10:], key=lambda x: x[0])
                ]
            }

class MetricsLogger:
    def __init__(self, metrics: EventMetrics, log_interval: int = 60):
        self.metrics = metrics
        self.log_interval = log_interval
        self._stop_event = threading.Event()
        self._thread = None
        
    def start(self):
        """Start periodic metrics logging"""
        if self._thread is not None:
            return
            
        def _logging_loop():
            while not self._stop_event.is_set():
                self._log_metrics()
                self._stop_event.wait(self.log_interval)
                
        self._thread = threading.Thread(target=_logging_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop metrics logging"""
        if self._thread is None:
            return
            
        self._stop_event.set()
        self._thread.join()
        self._thread = None
        
    def _log_metrics(self):
        """Log current metrics"""
        metrics = self.metrics.get_metrics_report()
        
        logging.info("=== Metrics Report ===")
        logging.info(f"Events per minute (5m avg): {metrics['events_per_minute']:.2f}")
        logging.info(f"Total events collected: {metrics['total_events']}")
        logging.info(f"Failed polls: {metrics['failed_polls']}")
        
        if metrics['last_successful_poll'] is not None:
            logging.info(f"Last successful poll: {metrics['last_successful_poll']:.1f} seconds ago")
            
        if metrics['last_error']:
            logging.info(f"Last error: {metrics['last_error']}")
            
        if metrics['recent_counts']:
            logging.info("Recent event counts:")
            for entry in metrics['recent_counts']:
                logging.info(f"  {entry['timestamp']}: {entry['count']} events")
        
        logging.info("=====================")

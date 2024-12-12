from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime

@dataclass
class AuditEvent:
    timestamp: float
    user: str
    action: str
    details: Dict[str, Any]
    event_id: str

    @classmethod
    def create(cls, user: str, action: str, details: Dict[str, Any]) -> 'AuditEvent':
        """Factory method to create a new audit event"""
        return cls(
            timestamp=datetime.now().timestamp(),
            user=user,
            action=action,
            details=details,
            event_id=f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user}"
        )

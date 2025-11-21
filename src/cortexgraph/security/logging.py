import json
import logging
from typing import Any

from ..storage.models import SecurityEvent, SecurityEventType

logger = logging.getLogger("cortexgraph.security")


def log_security_event(
    event_type: SecurityEventType,
    endpoint: str,
    source_ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Log a security-relevant event."""
    event = SecurityEvent(
        event_type=event_type,
        endpoint=endpoint,
        source_ip=source_ip,
        details=details or {},
    )

    # Log as structured JSON for machine parsing
    logger.info(
        json.dumps(
            {
                "security_event": True,
                "timestamp": event.timestamp,
                "type": event.event_type.value,
                "endpoint": event.endpoint,
                "source_ip": event.source_ip,
                "details": event.details,
            }
        )
    )

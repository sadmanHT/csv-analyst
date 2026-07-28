"""
Structured Observability and Tracing Logger
"""

import json
import time
import logging
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("csv_analyst")

def log_event(event_type: str, request_id: str, **kwargs: Any) -> None:
    """Emit a structured JSON log event for tracing and metrics aggregation."""
    log_data = {
        "event_type": event_type,
        "request_id": request_id,
        "timestamp": time.time(),
        **kwargs,
    }
    logger.info(json.dumps(log_data, default=str))

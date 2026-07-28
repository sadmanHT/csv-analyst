"""
Active Request Cancellation Registry
"""

import logging
from typing import Set

logger = logging.getLogger(__name__)

_cancelled_requests: Set[str] = set()

def cancel_request(request_id: str) -> bool:
    """Register a request ID as cancelled."""
    if not request_id:
        return False
    _cancelled_requests.add(request_id.lower())
    logger.info("Request %s registered as cancelled", request_id)
    return True

def is_cancelled(request_id: str | None) -> bool:
    """Check whether a request has been cancelled by the user."""
    if not request_id:
        return False
    return request_id.lower() in _cancelled_requests

def clear_cancellation(request_id: str | None) -> None:
    """Remove a request ID from the cancellation set."""
    if request_id:
        _cancelled_requests.discard(request_id.lower())

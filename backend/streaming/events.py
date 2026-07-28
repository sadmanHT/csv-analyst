"""
SSE Event Catalog and Formatter with Event Sequence and Single Terminal Enforcement
"""

import json
import time
import uuid
from enum import Enum
from typing import Callable, Any

class EventType(str, Enum):
    ANALYSIS_STARTED = "analysis_started"
    ROUTE_SELECTED = "route_selected"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    PROGRESS = "progress"
    PARTIAL_RESULT = "partial_result"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"

def make_sse_emitter(endpoint: str, session_id: str, request_id: str | None = None) -> Callable[[dict[str, Any]], str]:
    """Create an SSE encoder enforcing sequence numbers, request IDs, and terminal events."""
    req_id = request_id or str(uuid.uuid4())
    started_at = time.time()
    sequence = 0
    terminal_emitted = False

    def emit(payload: dict[str, Any]) -> str:
        nonlocal sequence, terminal_emitted
        if terminal_emitted:
            # Prevent sending post-terminal event noise
            return ""

        sequence += 1
        event = {**payload}
        if "request_id" not in event:
            event["request_id"] = req_id

        meta = {**event.get("meta", {})}
        meta.update({
            "request_id": req_id,
            "endpoint": endpoint,
            "session_id": session_id,
            "elapsed_ms": int((time.time() - started_at) * 1000),
            "sequence": sequence,
        })
        event["meta"] = meta

        event_type = event.get("type") or event.get("step")
        if event_type in ("analysis_completed", "analysis_failed", "request_cancelled", "done") or event.get("status") in ("complete", "failed", "cancelled"):
            terminal_emitted = True

        return f"data: {json.dumps(event, default=str)}\n\n"

    return emit

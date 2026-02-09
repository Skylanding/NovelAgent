"""Event middleware for logging, filtering, and replay."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from storyforge.events.types import Event

logger = logging.getLogger(__name__)


class EventLogger:
    """Logs all events for debugging."""

    async def __call__(self, event: Event) -> Optional[Event]:
        logger.debug(
            "[%s] -> %s (id=%s, corr=%s)",
            event.source_agent,
            event.event_type.value,
            event.event_id[:8],
            event.correlation_id[:8] if event.correlation_id else "none",
        )
        return event


class EventFileLogger:
    """Persists events to a JSONL file for replay/debugging."""

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    async def __call__(self, event: Event) -> Optional[Event]:
        record = {
            "event_type": event.event_type.value,
            "source_agent": event.source_agent,
            "target_agent": event.target_agent,
            "event_id": event.event_id,
            "correlation_id": event.correlation_id,
            "chapter_number": event.chapter_number,
            "scene_index": event.scene_index,
            "timestamp": event.timestamp.isoformat(),
            "payload_keys": list(event.payload.keys()),
        }
        with open(self._log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        return event

"""Event types and data structures for the StoryForge event system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EventType(str, Enum):
    """All event types in the StoryForge pub/sub system."""

    # Plot events
    CHAPTER_PLAN_REQUEST = "chapter_plan_request"
    CHAPTER_PLAN_READY = "chapter_plan_ready"
    SCENE_PLAN_REQUEST = "scene_plan_request"
    SCENE_PLAN_READY = "scene_plan_ready"
    PACING_CHECK_REQUEST = "pacing_check_request"
    PACING_FEEDBACK = "pacing_feedback"

    # World events
    WORLD_QUERY = "world_query"
    WORLD_RESPONSE = "world_response"
    SETTING_VALIDATION_REQUEST = "setting_validation_request"
    SETTING_VALIDATION_RESULT = "setting_validation_result"
    LORE_CHECK = "lore_check"
    LORE_RESPONSE = "lore_response"

    # Character events
    CHARACTER_REACTION_REQUEST = "character_reaction_request"
    CHARACTER_REACTION = "character_reaction"
    DIALOGUE_REQUEST = "dialogue_request"
    DIALOGUE_RESPONSE = "dialogue_response"
    EMOTIONAL_STATE_UPDATE = "emotional_state_update"

    # Character system events (new)
    SKILL_ACTIVATION = "skill_activation"
    SKILL_ACTIVATION_RESULT = "skill_activation_result"
    RELATIONSHIP_UPDATE = "relationship_update"
    RELATIONSHIP_UPDATE_RESULT = "relationship_update_result"
    CHARACTER_CONSTRAINT_CHECK = "character_constraint_check"
    CHARACTER_CONSTRAINT_RESULT = "character_constraint_result"

    # Writing events
    SCENE_DRAFT_REQUEST = "scene_draft_request"
    SCENE_DRAFT_READY = "scene_draft_ready"
    REVISION_REQUEST = "revision_request"
    REVISION_READY = "revision_ready"
    CHAPTER_ASSEMBLED = "chapter_assembled"

    # Pipeline control events
    PIPELINE_STAGE_START = "pipeline_stage_start"
    PIPELINE_STAGE_COMPLETE = "pipeline_stage_complete"
    PIPELINE_ERROR = "pipeline_error"

    # Review events
    CONSISTENCY_CHECK_REQUEST = "consistency_check_request"
    CONSISTENCY_CHECK_RESULT = "consistency_check_result"
    QUALITY_CHECK_REQUEST = "quality_check_request"
    QUALITY_CHECK_RESULT = "quality_check_result"


@dataclass
class Event:
    """A single event in the pub/sub system."""

    event_type: EventType
    payload: dict[str, Any]
    source_agent: str
    target_agent: Optional[str] = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    chapter_number: Optional[int] = None
    scene_index: Optional[int] = None

    def create_response(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        source_agent: str,
    ) -> Event:
        """Create a response event linked via correlation_id."""
        return Event(
            event_type=event_type,
            payload=payload,
            source_agent=source_agent,
            correlation_id=self.event_id,
            chapter_number=self.chapter_number,
            scene_index=self.scene_index,
        )

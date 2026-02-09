"""Emotional state machine for character behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EmotionCategory(str, Enum):
    """High-level emotion categories."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CONFLICTED = "conflicted"


# Valid emotional states and their categories
EMOTION_TAXONOMY: dict[str, EmotionCategory] = {
    # Neutral states
    "neutral": EmotionCategory.NEUTRAL,
    "calm": EmotionCategory.NEUTRAL,
    "focused": EmotionCategory.NEUTRAL,
    "contemplative": EmotionCategory.NEUTRAL,
    "curious": EmotionCategory.NEUTRAL,
    "observant": EmotionCategory.NEUTRAL,
    # Positive states
    "hopeful": EmotionCategory.POSITIVE,
    "determined": EmotionCategory.POSITIVE,
    "confident": EmotionCategory.POSITIVE,
    "joyful": EmotionCategory.POSITIVE,
    "relieved": EmotionCategory.POSITIVE,
    "grateful": EmotionCategory.POSITIVE,
    "affectionate": EmotionCategory.POSITIVE,
    "excited": EmotionCategory.POSITIVE,
    "proud": EmotionCategory.POSITIVE,
    "content": EmotionCategory.POSITIVE,
    # Negative states
    "anxious": EmotionCategory.NEGATIVE,
    "fearful": EmotionCategory.NEGATIVE,
    "angry": EmotionCategory.NEGATIVE,
    "grieving": EmotionCategory.NEGATIVE,
    "frustrated": EmotionCategory.NEGATIVE,
    "desperate": EmotionCategory.NEGATIVE,
    "guilty": EmotionCategory.NEGATIVE,
    "ashamed": EmotionCategory.NEGATIVE,
    "bitter": EmotionCategory.NEGATIVE,
    "jealous": EmotionCategory.NEGATIVE,
    "lonely": EmotionCategory.NEGATIVE,
    "melancholic": EmotionCategory.NEGATIVE,
    "disappointed": EmotionCategory.NEGATIVE,
    # Conflicted states
    "conflicted": EmotionCategory.CONFLICTED,
    "torn": EmotionCategory.CONFLICTED,
    "suspicious": EmotionCategory.CONFLICTED,
    "wary": EmotionCategory.CONFLICTED,
    "ambivalent": EmotionCategory.CONFLICTED,
    "resigned": EmotionCategory.CONFLICTED,
}


# Suggested valid state transitions (soft constraints)
TRANSITION_SUGGESTIONS: dict[str, list[str]] = {
    "neutral": ["anxious", "hopeful", "focused", "curious", "wary", "calm"],
    "calm": ["neutral", "content", "contemplative", "focused"],
    "anxious": ["fearful", "determined", "relieved", "neutral", "desperate", "hopeful"],
    "fearful": ["anxious", "determined", "desperate", "relieved", "paralyzed"],
    "determined": ["confident", "frustrated", "hopeful", "neutral", "exhausted"],
    "hopeful": ["joyful", "disappointed", "determined", "anxious", "excited"],
    "angry": ["frustrated", "determined", "guilty", "neutral", "bitter"],
    "grieving": ["angry", "neutral", "hopeful", "guilty", "melancholic"],
    "conflicted": ["determined", "anxious", "relieved", "neutral", "resigned"],
    "frustrated": ["angry", "determined", "resigned", "neutral"],
    "confident": ["proud", "anxious", "determined", "neutral"],
    "guilty": ["ashamed", "determined", "relieved", "neutral"],
    "relieved": ["grateful", "neutral", "hopeful", "calm"],
}


@dataclass
class EmotionalTransition:
    """A transition between emotional states."""

    from_state: str
    to_state: str
    trigger_type: str
    """'event', 'dialogue', 'realization', 'time', or 'external'."""

    trigger_description: str
    intensity_change: int
    """How intensity shifts (-5 to +5)."""


class EmotionalStateMachine:
    """Manages emotional state transitions for a character."""

    # Character type volatility multipliers
    TYPE_VOLATILITY: dict[str, float] = {
        "protagonist": 1.2,  # More affected by events
        "antagonist": 0.8,  # More controlled
        "mentor": 0.6,  # Very stable
        "sidekick": 1.3,  # Reactive
        "threshold_guardian": 0.7,  # Steady
        "supporting": 1.0,  # Normal
    }

    def __init__(self, character_type: str = "supporting") -> None:
        self.character_type = character_type
        self._transition_history: list[EmotionalTransition] = []

    @property
    def volatility(self) -> float:
        """Get the emotional volatility for this character type."""
        return self.TYPE_VOLATILITY.get(self.character_type, 1.0)

    def get_category(self, state: str) -> EmotionCategory:
        """Get the category for an emotional state."""
        return EMOTION_TAXONOMY.get(state.lower(), EmotionCategory.NEUTRAL)

    def can_transition(self, from_state: str, to_state: str) -> bool:
        """
        Check if a transition is valid.
        This is a soft constraint - any transition is technically allowed,
        but some are more natural than others.
        """
        from_state = from_state.lower()
        to_state = to_state.lower()

        # Same state is always valid
        if from_state == to_state:
            return True

        # Check if it's a suggested transition
        if from_state in TRANSITION_SUGGESTIONS:
            if to_state in TRANSITION_SUGGESTIONS[from_state]:
                return True

        # Allow any transition (soft constraint for LLM)
        return True

    def is_natural_transition(self, from_state: str, to_state: str) -> bool:
        """Check if a transition is a natural/suggested one."""
        from_state = from_state.lower()
        to_state = to_state.lower()

        if from_state in TRANSITION_SUGGESTIONS:
            return to_state in TRANSITION_SUGGESTIONS[from_state]
        return False

    def suggest_transitions(self, current_state: str) -> list[str]:
        """Suggest natural next states from current state."""
        current_state = current_state.lower()
        return TRANSITION_SUGGESTIONS.get(current_state, ["neutral"])

    def record_transition(
        self,
        from_state: str,
        to_state: str,
        trigger_type: str,
        trigger_description: str,
        intensity_change: int = 0,
    ) -> EmotionalTransition:
        """Record a state transition."""
        transition = EmotionalTransition(
            from_state=from_state.lower(),
            to_state=to_state.lower(),
            trigger_type=trigger_type,
            trigger_description=trigger_description,
            intensity_change=intensity_change,
        )
        self._transition_history.append(transition)
        return transition

    def get_recent_transitions(self, count: int = 5) -> list[EmotionalTransition]:
        """Get the most recent state transitions."""
        return self._transition_history[-count:]

    def compute_intensity_change(
        self,
        event_severity: int,
        is_positive: bool,
    ) -> int:
        """
        Compute how much emotional intensity should change.
        event_severity: 1-10 scale
        is_positive: whether the event is positive for the character
        """
        base_change = event_severity // 2
        adjusted = int(base_change * self.volatility)

        # Cap at -5 to +5
        return max(-5, min(5, adjusted if is_positive else -adjusted))

    def format_for_prompt(
        self,
        current_state: str,
        intensity: int,
        previous_states: list[str],
    ) -> str:
        """Format emotional state info for inclusion in prompts."""
        category = self.get_category(current_state)
        suggestions = self.suggest_transitions(current_state)

        lines = [
            f"Current emotional state: {current_state} (intensity {intensity}/10)",
            f"Emotional category: {category.value}",
        ]

        if previous_states:
            recent = previous_states[-3:]
            lines.append(f"Recent emotional journey: {' -> '.join(recent)} -> {current_state}")

        lines.append(f"Natural next states: {', '.join(suggestions[:4])}")

        return "\n".join(lines)

    def parse_emotional_shift(self, shift_text: str) -> Optional[tuple[str, str]]:
        """
        Parse an emotional shift string like 'anxious -> determined'.
        Returns (from_state, to_state) or None if invalid format.
        """
        if "->" not in shift_text:
            return None

        parts = shift_text.split("->")
        if len(parts) != 2:
            return None

        from_state = parts[0].strip().lower()
        to_state = parts[1].strip().lower()

        return (from_state, to_state)

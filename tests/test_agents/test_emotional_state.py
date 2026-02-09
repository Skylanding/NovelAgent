"""Tests for EmotionalStateMachine."""

import pytest

from storyforge.agents.character.emotional_state import (
    EmotionCategory,
    EmotionalStateMachine,
    EMOTION_TAXONOMY,
    TRANSITION_SUGGESTIONS,
)


class TestEmotionalStateMachine:
    def setup_method(self):
        self.machine = EmotionalStateMachine(character_type="protagonist")

    def test_volatility_protagonist(self):
        assert self.machine.volatility == 1.2

    def test_volatility_mentor(self):
        m = EmotionalStateMachine(character_type="mentor")
        assert m.volatility == 0.6

    def test_volatility_unknown_type(self):
        m = EmotionalStateMachine(character_type="unknown")
        assert m.volatility == 1.0

    def test_get_category_known(self):
        assert self.machine.get_category("anxious") == EmotionCategory.NEGATIVE
        assert self.machine.get_category("hopeful") == EmotionCategory.POSITIVE
        assert self.machine.get_category("neutral") == EmotionCategory.NEUTRAL
        assert self.machine.get_category("conflicted") == EmotionCategory.CONFLICTED

    def test_get_category_case_insensitive(self):
        assert self.machine.get_category("ANXIOUS") == EmotionCategory.NEGATIVE

    def test_get_category_unknown(self):
        assert self.machine.get_category("nonexistent") == EmotionCategory.NEUTRAL

    def test_can_transition_same_state(self):
        assert self.machine.can_transition("anxious", "anxious") is True

    def test_can_transition_suggested(self):
        assert self.machine.can_transition("anxious", "determined") is True

    def test_can_transition_any(self):
        # Soft constraint: all transitions are allowed
        assert self.machine.can_transition("joyful", "angry") is True

    def test_is_natural_transition_true(self):
        assert self.machine.is_natural_transition("anxious", "determined") is True

    def test_is_natural_transition_false(self):
        assert self.machine.is_natural_transition("calm", "angry") is False

    def test_suggest_transitions_known(self):
        suggestions = self.machine.suggest_transitions("neutral")
        assert "anxious" in suggestions
        assert "hopeful" in suggestions

    def test_suggest_transitions_unknown(self):
        suggestions = self.machine.suggest_transitions("nonexistent")
        assert suggestions == ["neutral"]

    def test_record_transition(self):
        t = self.machine.record_transition(
            from_state="neutral",
            to_state="anxious",
            trigger_type="event",
            trigger_description="heard bad news",
            intensity_change=2,
        )
        assert t.from_state == "neutral"
        assert t.to_state == "anxious"

    def test_get_recent_transitions(self):
        for i in range(10):
            self.machine.record_transition(
                from_state=f"state_{i}",
                to_state=f"state_{i+1}",
                trigger_type="event",
                trigger_description=f"event {i}",
            )
        recent = self.machine.get_recent_transitions(count=3)
        assert len(recent) == 3
        assert recent[-1].to_state == "state_10"

    def test_compute_intensity_change_positive(self):
        change = self.machine.compute_intensity_change(event_severity=8, is_positive=True)
        assert change > 0
        assert -5 <= change <= 5

    def test_compute_intensity_change_negative(self):
        change = self.machine.compute_intensity_change(event_severity=8, is_positive=False)
        assert change < 0
        assert -5 <= change <= 5

    def test_compute_intensity_change_capped(self):
        change = self.machine.compute_intensity_change(event_severity=10, is_positive=True)
        assert change <= 5

    def test_format_for_prompt(self):
        text = self.machine.format_for_prompt(
            current_state="anxious",
            intensity=7,
            previous_states=["neutral", "hopeful"],
        )
        assert "anxious" in text
        assert "7/10" in text
        assert "neutral" in text

    def test_format_for_prompt_no_history(self):
        text = self.machine.format_for_prompt(
            current_state="neutral",
            intensity=5,
            previous_states=[],
        )
        assert "neutral" in text
        assert "journey" not in text

    def test_parse_emotional_shift_valid(self):
        result = self.machine.parse_emotional_shift("anxious -> determined")
        assert result == ("anxious", "determined")

    def test_parse_emotional_shift_no_arrow(self):
        result = self.machine.parse_emotional_shift("just anxious")
        assert result is None

    def test_parse_emotional_shift_multiple_arrows(self):
        result = self.machine.parse_emotional_shift("a -> b -> c")
        assert result is None

    def test_parse_emotional_shift_case(self):
        result = self.machine.parse_emotional_shift("Anxious -> Determined")
        assert result == ("anxious", "determined")

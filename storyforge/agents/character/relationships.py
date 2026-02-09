"""Relationship system for character interactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from storyforge.agents.character.sheet import RelationshipState


class RelationshipType(str, Enum):
    """Types of relationships between characters."""

    ALLY = "ally"
    RIVAL = "rival"
    MENTOR_STUDENT = "mentor-student"
    ROMANTIC = "romantic"
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    FAMILIAL = "familial"
    PROFESSIONAL = "professional"
    WARY = "wary"
    COMPLEX = "complex"


@dataclass
class RelationshipModifier:
    """Modifies dialogue/behavior based on relationship type."""

    tone_adjustment: str
    """How tone shifts when interacting with this relationship type."""

    trust_threshold: int
    """Minimum trust level for certain cooperative behaviors."""

    dialogue_formality: str
    """'formal', 'casual', 'intimate', or 'hostile'."""

    willingness_to_help: float
    """0.0 to 1.0 base willingness to assist."""

    information_sharing: float
    """0.0 to 1.0 base willingness to share information."""


# Pre-defined relationship modifiers
RELATIONSHIP_MODIFIERS: dict[RelationshipType, RelationshipModifier] = {
    RelationshipType.ALLY: RelationshipModifier(
        tone_adjustment="supportive and warm",
        trust_threshold=-2,
        dialogue_formality="casual",
        willingness_to_help=0.9,
        information_sharing=0.8,
    ),
    RelationshipType.RIVAL: RelationshipModifier(
        tone_adjustment="competitive and guarded",
        trust_threshold=3,
        dialogue_formality="formal",
        willingness_to_help=0.3,
        information_sharing=0.2,
    ),
    RelationshipType.MENTOR_STUDENT: RelationshipModifier(
        tone_adjustment="instructive and respectful",
        trust_threshold=-5,
        dialogue_formality="respectful",
        willingness_to_help=0.95,
        information_sharing=0.7,
    ),
    RelationshipType.ROMANTIC: RelationshipModifier(
        tone_adjustment="affectionate and protective",
        trust_threshold=-3,
        dialogue_formality="intimate",
        willingness_to_help=1.0,
        information_sharing=0.9,
    ),
    RelationshipType.HOSTILE: RelationshipModifier(
        tone_adjustment="cold, aggressive, or contemptuous",
        trust_threshold=8,
        dialogue_formality="hostile",
        willingness_to_help=0.0,
        information_sharing=0.0,
    ),
    RelationshipType.NEUTRAL: RelationshipModifier(
        tone_adjustment="polite but distant",
        trust_threshold=0,
        dialogue_formality="formal",
        willingness_to_help=0.5,
        information_sharing=0.3,
    ),
    RelationshipType.FAMILIAL: RelationshipModifier(
        tone_adjustment="familiar with underlying complexity",
        trust_threshold=-4,
        dialogue_formality="casual",
        willingness_to_help=0.85,
        information_sharing=0.75,
    ),
    RelationshipType.PROFESSIONAL: RelationshipModifier(
        tone_adjustment="businesslike and focused",
        trust_threshold=0,
        dialogue_formality="formal",
        willingness_to_help=0.6,
        information_sharing=0.5,
    ),
    RelationshipType.WARY: RelationshipModifier(
        tone_adjustment="cautious and watchful",
        trust_threshold=2,
        dialogue_formality="formal",
        willingness_to_help=0.3,
        information_sharing=0.2,
    ),
    RelationshipType.COMPLEX: RelationshipModifier(
        tone_adjustment="varies based on context and history",
        trust_threshold=0,
        dialogue_formality="contextual",
        willingness_to_help=0.5,
        information_sharing=0.4,
    ),
}


class RelationshipManager:
    """Manages relationship states and interactions."""

    @staticmethod
    def get_modifier(rel_type: RelationshipType) -> RelationshipModifier:
        """Get the modifier for a relationship type."""
        return RELATIONSHIP_MODIFIERS.get(
            rel_type, RELATIONSHIP_MODIFIERS[RelationshipType.NEUTRAL]
        )

    @staticmethod
    def parse_relationship_type(type_str: str) -> RelationshipType:
        """Parse a relationship type string, with fallback to COMPLEX."""
        try:
            return RelationshipType(type_str.lower().replace(" ", "-"))
        except ValueError:
            return RelationshipType.COMPLEX

    @staticmethod
    def compute_interaction_context(
        relationship: "RelationshipState",
        scene_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute how a relationship affects an interaction."""
        rel_type = RelationshipManager.parse_relationship_type(
            relationship.relationship_type
        )
        modifier = RelationshipManager.get_modifier(rel_type)

        # Adjust for trust level (-10 to +10 normalized to 0-1)
        trust_factor = (relationship.trust_level + 10) / 20

        # Calculate effective willingness values
        effective_help = modifier.willingness_to_help * trust_factor
        effective_share = modifier.information_sharing * trust_factor

        # Get recent history for context
        recent_history = (
            relationship.history[-3:] if relationship.history else []
        )

        return {
            "relationship_type": relationship.relationship_type,
            "tone": modifier.tone_adjustment,
            "formality": modifier.dialogue_formality,
            "trust_level": relationship.trust_level,
            "help_likelihood": effective_help,
            "share_info_likelihood": effective_share,
            "recent_history": recent_history,
            "current_tension": relationship.current_tension,
            "trust_threshold_met": relationship.trust_level >= modifier.trust_threshold,
        }

    @staticmethod
    def update_trust(
        relationship: "RelationshipState",
        event: str,
        delta: int,
    ) -> "RelationshipState":
        """Update trust level based on an event."""
        new_trust = max(-10, min(10, relationship.trust_level + delta))
        relationship.trust_level = new_trust
        relationship.history.append(f"{event} (trust {delta:+d})")
        return relationship

    @staticmethod
    def suggest_relationship_evolution(
        relationship: "RelationshipState",
        events: list[str],
    ) -> Optional[str]:
        """
        Suggest how a relationship might evolve based on recent events.
        Returns a suggestion string or None.
        """
        if not events:
            return None

        # Analyze trust trajectory
        if relationship.trust_level >= 7:
            return "Relationship deepening toward strong bond"
        elif relationship.trust_level <= -7:
            return "Relationship deteriorating toward open hostility"
        elif relationship.trust_level >= 3 and relationship.relationship_type == "rival":
            return "Rivalry may be shifting toward grudging respect"
        elif relationship.trust_level <= -3 and relationship.relationship_type == "ally":
            return "Alliance showing signs of strain"

        return None

    @staticmethod
    def format_for_prompt(
        relationships: list["RelationshipState"],
        characters_present: list[str],
    ) -> str:
        """Format relationship info for inclusion in prompts."""
        relevant = [r for r in relationships if r.target_character in characters_present]

        if not relevant:
            return "No established relationships with characters present."

        lines = []
        for rel in relevant:
            context = RelationshipManager.compute_interaction_context(rel, {})
            line = (
                f"- {rel.target_character}: {rel.relationship_type} "
                f"(trust: {rel.trust_level:+d}, tone: {context['tone']})"
            )
            if rel.current_tension:
                line += f"\n  Current tension: {rel.current_tension}"
            lines.append(line)

        return "RELATIONSHIP DYNAMICS:\n" + "\n".join(lines)

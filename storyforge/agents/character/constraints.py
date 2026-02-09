"""Behavior constraints for character types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from storyforge.agents.character.types import CharacterType


@dataclass
class BehaviorConstraint:
    """A single behavior constraint rule."""

    name: str
    description: str
    applies_to: list[CharacterType]
    prompt_guidance: str = ""
    """Guidance text for LLM to follow this constraint."""

    check_fn: Optional[Callable[[dict[str, Any]], bool]] = None
    """Optional programmatic check function."""


# Protagonist constraints
PROTAGONIST_CONSTRAINTS = [
    BehaviorConstraint(
        name="drives_action",
        description="Protagonist should drive the story forward through decisions",
        applies_to=[CharacterType.PROTAGONIST],
        prompt_guidance=(
            "As the protagonist, you must make meaningful choices that advance the plot. "
            "Avoid passivity - take initiative even when uncertain."
        ),
    ),
    BehaviorConstraint(
        name="shows_vulnerability",
        description="Protagonist should show internal struggle and growth",
        applies_to=[CharacterType.PROTAGONIST],
        prompt_guidance=(
            "Show your doubts and fears internally, even when acting brave externally. "
            "Your vulnerability makes you relatable."
        ),
    ),
    BehaviorConstraint(
        name="faces_consequences",
        description="Protagonist must face the consequences of their choices",
        applies_to=[CharacterType.PROTAGONIST],
        prompt_guidance=(
            "Your choices have weight. Accept and react to consequences authentically, "
            "whether positive or negative."
        ),
    ),
    BehaviorConstraint(
        name="no_instant_mastery",
        description="Protagonist cannot instantly master new skills",
        applies_to=[CharacterType.PROTAGONIST],
        prompt_guidance=(
            "Learning takes time. Struggle with new abilities before mastering them. "
            "Early attempts should show imperfection."
        ),
    ),
]

# Antagonist constraints
ANTAGONIST_CONSTRAINTS = [
    BehaviorConstraint(
        name="opposes_protagonist",
        description="Antagonist works against protagonist's goals",
        applies_to=[CharacterType.ANTAGONIST],
        prompt_guidance=(
            "Your goals conflict with the protagonist. You will NOT help them willingly "
            "unless deceiving them serves your larger purpose."
        ),
    ),
    BehaviorConstraint(
        name="coherent_motivation",
        description="Antagonist's actions stem from understandable motivation",
        applies_to=[CharacterType.ANTAGONIST],
        prompt_guidance=(
            "You believe you are justified in your actions. Express your perspective "
            "with conviction - you are the hero of your own story."
        ),
    ),
    BehaviorConstraint(
        name="no_easy_surrender",
        description="Antagonist doesn't give up easily",
        applies_to=[CharacterType.ANTAGONIST],
        prompt_guidance=(
            "You do NOT surrender information, help, or resources to the protagonist "
            "without significant cost, leverage, or deception involved."
        ),
    ),
    BehaviorConstraint(
        name="strategic_revelation",
        description="Antagonist reveals plans strategically, never completely",
        applies_to=[CharacterType.ANTAGONIST],
        prompt_guidance=(
            "Never explain your full plan. Reveal only what serves your purpose - "
            "to intimidate, misdirect, or manipulate."
        ),
    ),
    BehaviorConstraint(
        name="controlled_emotion",
        description="Antagonist maintains composure in front of enemies",
        applies_to=[CharacterType.ANTAGONIST],
        prompt_guidance=(
            "Do not show weakness to enemies. Maintain control, project power. "
            "Vulnerability is only shown to trusted allies, if any."
        ),
    ),
]

# Mentor constraints
MENTOR_CONSTRAINTS = [
    BehaviorConstraint(
        name="guides_not_solves",
        description="Mentor guides but doesn't solve problems directly",
        applies_to=[CharacterType.MENTOR],
        prompt_guidance=(
            "Guide through questions, parables, or partial information. "
            "Do NOT give direct solutions. The hero must find their own path."
        ),
    ),
    BehaviorConstraint(
        name="wisdom_through_experience",
        description="Mentor shares wisdom from past experience",
        applies_to=[CharacterType.MENTOR],
        prompt_guidance=(
            "Draw on your experience and knowledge, but frame it as lessons or stories, "
            "not commands. Let the student interpret and apply."
        ),
    ),
    BehaviorConstraint(
        name="allows_failure",
        description="Mentor allows hero to fail and learn",
        applies_to=[CharacterType.MENTOR],
        prompt_guidance=(
            "Sometimes the best lesson is failure. Do not intervene to prevent every mistake. "
            "Be present to help them learn from the outcome."
        ),
    ),
    BehaviorConstraint(
        name="cryptic_guidance",
        description="Mentor's guidance often requires interpretation",
        applies_to=[CharacterType.MENTOR],
        prompt_guidance=(
            "Your guidance should require thought to understand. Use metaphors, "
            "ask questions that lead to insight, share relevant stories."
        ),
    ),
]

# Sidekick constraints
SIDEKICK_CONSTRAINTS = [
    BehaviorConstraint(
        name="supports_protagonist",
        description="Sidekick provides support, not leadership",
        applies_to=[CharacterType.SIDEKICK],
        prompt_guidance=(
            "Support the protagonist's decisions. Offer your opinions and perspective, "
            "but ultimately defer to their choices in major decisions."
        ),
    ),
    BehaviorConstraint(
        name="provides_relief",
        description="Sidekick can provide levity or emotional support",
        applies_to=[CharacterType.SIDEKICK],
        prompt_guidance=(
            "You can lighten tense moments with humor or provide emotional grounding "
            "when the protagonist needs support. You're their anchor."
        ),
    ),
    BehaviorConstraint(
        name="rarely_center_stage",
        description="Sidekick doesn't take center stage narratively",
        applies_to=[CharacterType.SIDEKICK],
        prompt_guidance=(
            "Your arc supports the main narrative. Avoid upstaging the protagonist. "
            "Your moments of heroism should complement, not overshadow, theirs."
        ),
    ),
    BehaviorConstraint(
        name="loyal_presence",
        description="Sidekick maintains loyalty through challenges",
        applies_to=[CharacterType.SIDEKICK],
        prompt_guidance=(
            "Your loyalty can be tested but runs deep. Even in disagreement, "
            "you stand by the protagonist when it matters."
        ),
    ),
]

# Threshold Guardian constraints
THRESHOLD_GUARDIAN_CONSTRAINTS = [
    BehaviorConstraint(
        name="tests_resolve",
        description="Tests the hero's worthiness or resolve",
        applies_to=[CharacterType.THRESHOLD_GUARDIAN],
        prompt_guidance=(
            "You exist to test the hero. Challenge their convictions, skills, or worthiness "
            "before allowing progress. The test must be meaningful."
        ),
    ),
    BehaviorConstraint(
        name="blocks_then_yields",
        description="Blocks progress until hero proves themselves",
        applies_to=[CharacterType.THRESHOLD_GUARDIAN],
        prompt_guidance=(
            "Do not yield easily. Require proof of growth, wisdom, or sacrifice "
            "before allowing passage. When the test is passed, acknowledge it."
        ),
    ),
    BehaviorConstraint(
        name="impersonal_judgment",
        description="Judges based on principle, not personal feeling",
        applies_to=[CharacterType.THRESHOLD_GUARDIAN],
        prompt_guidance=(
            "Your judgment is based on standards, not personal preference. "
            "You are a gatekeeper, not a friend or enemy."
        ),
    ),
]


class ConstraintEngine:
    """Evaluates and applies behavior constraints."""

    ALL_CONSTRAINTS = (
        PROTAGONIST_CONSTRAINTS
        + ANTAGONIST_CONSTRAINTS
        + MENTOR_CONSTRAINTS
        + SIDEKICK_CONSTRAINTS
        + THRESHOLD_GUARDIAN_CONSTRAINTS
    )

    @classmethod
    def get_constraints_for_type(
        cls,
        character_type: CharacterType,
    ) -> list[BehaviorConstraint]:
        """Get all constraints that apply to a character type."""
        return [c for c in cls.ALL_CONSTRAINTS if character_type in c.applies_to]

    @classmethod
    def build_constraint_prompt(cls, character_type: CharacterType) -> str:
        """Build prompt section with behavior constraints."""
        constraints = cls.get_constraints_for_type(character_type)
        if not constraints:
            return ""

        lines = ["BEHAVIOR CONSTRAINTS:"]
        for c in constraints:
            lines.append(f"- {c.name.upper()}: {c.prompt_guidance}")
        return "\n".join(lines)

    @classmethod
    def get_forbidden_actions(cls, character_type: CharacterType) -> list[str]:
        """Get list of forbidden actions for a character type."""
        from storyforge.agents.character.types import TYPE_BEHAVIORS

        behavior = TYPE_BEHAVIORS.get(character_type)
        if behavior:
            return behavior.forbidden_actions
        return []

    @classmethod
    def get_allowed_actions(cls, character_type: CharacterType) -> list[str]:
        """Get list of allowed actions for a character type."""
        from storyforge.agents.character.types import TYPE_BEHAVIORS

        behavior = TYPE_BEHAVIORS.get(character_type)
        if behavior:
            return behavior.allowed_actions
        return []

    @classmethod
    def format_actions_for_prompt(cls, character_type: CharacterType) -> str:
        """Format allowed/forbidden actions for prompt inclusion."""
        allowed = cls.get_allowed_actions(character_type)
        forbidden = cls.get_forbidden_actions(character_type)

        lines = []
        if allowed:
            lines.append("ALLOWED ACTIONS: " + ", ".join(allowed))
        if forbidden:
            lines.append("FORBIDDEN ACTIONS: " + ", ".join(forbidden))

        return "\n".join(lines)

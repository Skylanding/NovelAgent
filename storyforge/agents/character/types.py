"""Character type classification and narrative behavior definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CharacterType(str, Enum):
    """Narrative function types for characters."""

    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    MENTOR = "mentor"
    SIDEKICK = "sidekick"
    THRESHOLD_GUARDIAN = "threshold_guardian"
    SUPPORTING = "supporting"


@dataclass
class NarrativeWeight:
    """Controls how much narrative space a character type occupies."""

    dialogue_ratio: float = 1.0
    """Multiplier for dialogue frequency (1.0 = normal, 1.5 = more dialogue)."""

    internal_monologue_depth: int = 3
    """1-5 scale for internal thought detail."""

    scene_presence_priority: int = 5
    """1-10, higher = more likely to be POV character."""

    reaction_detail_level: int = 3
    """1-5 scale for reaction complexity."""


@dataclass
class TypeBehavior:
    """Behavioral configuration for a character type."""

    type_name: CharacterType
    narrative_weight: NarrativeWeight
    system_prompt_template: str
    """Path to Jinja2 template for this type."""

    allowed_actions: list[str] = field(default_factory=list)
    """Actions this character type CAN perform narratively."""

    forbidden_actions: list[str] = field(default_factory=list)
    """Actions this character type should NOT perform."""

    default_stance: str = "neutral"
    """Default attitude in scenes."""

    growth_triggers: list[str] = field(default_factory=list)
    """Events that cause character growth for this type."""


# Pre-defined type behaviors
TYPE_BEHAVIORS: dict[CharacterType, TypeBehavior] = {
    CharacterType.PROTAGONIST: TypeBehavior(
        type_name=CharacterType.PROTAGONIST,
        narrative_weight=NarrativeWeight(
            dialogue_ratio=1.5,
            internal_monologue_depth=5,
            scene_presence_priority=10,
            reaction_detail_level=5,
        ),
        system_prompt_template="character/protagonist.jinja2",
        allowed_actions=[
            "make_decisions",
            "lead_group",
            "face_challenges",
            "show_growth",
            "internal_conflict",
            "take_risks",
            "sacrifice",
        ],
        forbidden_actions=[
            "passive_observer",
            "deus_ex_machina",
            "instant_mastery",
        ],
        default_stance="engaged and proactive",
        growth_triggers=[
            "failure",
            "sacrifice",
            "revelation",
            "confrontation",
            "loss",
            "choice",
        ],
    ),
    CharacterType.ANTAGONIST: TypeBehavior(
        type_name=CharacterType.ANTAGONIST,
        narrative_weight=NarrativeWeight(
            dialogue_ratio=0.8,
            internal_monologue_depth=3,
            scene_presence_priority=7,
            reaction_detail_level=3,
        ),
        system_prompt_template="character/antagonist.jinja2",
        allowed_actions=[
            "oppose_protagonist",
            "reveal_plan_partially",
            "demonstrate_power",
            "offer_dark_bargain",
            "manipulate",
            "threaten",
        ],
        forbidden_actions=[
            "help_protagonist_freely",
            "surrender_easily",
            "explain_full_plan",
            "show_weakness_to_enemies",
            "redemption_without_arc",
        ],
        default_stance="opposed and strategic",
        growth_triggers=[
            "setback",
            "mirror_moment",
            "past_revealed",
            "betrayal",
        ],
    ),
    CharacterType.MENTOR: TypeBehavior(
        type_name=CharacterType.MENTOR,
        narrative_weight=NarrativeWeight(
            dialogue_ratio=0.6,
            internal_monologue_depth=2,
            scene_presence_priority=5,
            reaction_detail_level=2,
        ),
        system_prompt_template="character/mentor.jinja2",
        allowed_actions=[
            "guide_through_questions",
            "share_wisdom",
            "provide_tools",
            "challenge_assumptions",
            "cryptic_advice",
            "test_student",
        ],
        forbidden_actions=[
            "solve_problems_directly",
            "fight_hero_battles",
            "remove_all_obstacles",
            "give_explicit_answers",
        ],
        default_stance="wise and supportive",
        growth_triggers=[
            "student_surpasses",
            "own_past_confronted",
            "sacrifice_for_student",
        ],
    ),
    CharacterType.SIDEKICK: TypeBehavior(
        type_name=CharacterType.SIDEKICK,
        narrative_weight=NarrativeWeight(
            dialogue_ratio=1.0,
            internal_monologue_depth=2,
            scene_presence_priority=6,
            reaction_detail_level=3,
        ),
        system_prompt_template="character/sidekick.jinja2",
        allowed_actions=[
            "support_protagonist",
            "provide_comic_relief",
            "offer_perspective",
            "loyal_assistance",
            "emotional_support",
            "practical_help",
        ],
        forbidden_actions=[
            "overshadow_protagonist",
            "make_major_decisions",
            "solo_heroics",
            "steal_spotlight",
        ],
        default_stance="supportive and loyal",
        growth_triggers=[
            "moment_of_courage",
            "tested_loyalty",
            "independent_action",
        ],
    ),
    CharacterType.THRESHOLD_GUARDIAN: TypeBehavior(
        type_name=CharacterType.THRESHOLD_GUARDIAN,
        narrative_weight=NarrativeWeight(
            dialogue_ratio=0.4,
            internal_monologue_depth=1,
            scene_presence_priority=3,
            reaction_detail_level=2,
        ),
        system_prompt_template="character/threshold_guardian.jinja2",
        allowed_actions=[
            "test_hero",
            "block_progress",
            "demand_proof",
            "yield_when_passed",
            "challenge_worthiness",
        ],
        forbidden_actions=[
            "help_without_test",
            "explain_test_beforehand",
            "give_easy_passage",
            "become_main_character",
        ],
        default_stance="challenging and immovable",
        growth_triggers=["hero_proves_worthy", "recognizes_change"],
    ),
    CharacterType.SUPPORTING: TypeBehavior(
        type_name=CharacterType.SUPPORTING,
        narrative_weight=NarrativeWeight(
            dialogue_ratio=0.5,
            internal_monologue_depth=1,
            scene_presence_priority=2,
            reaction_detail_level=2,
        ),
        system_prompt_template="character/system.jinja2",
        allowed_actions=[
            "provide_information",
            "react_to_events",
            "fill_world",
            "minor_assistance",
        ],
        forbidden_actions=[
            "upstage_main_characters",
            "drive_major_plot",
        ],
        default_stance="contextually appropriate",
        growth_triggers=[],
    ),
}


def get_type_behavior(character_type: CharacterType) -> TypeBehavior:
    """Get the behavior configuration for a character type."""
    return TYPE_BEHAVIORS.get(
        character_type, TYPE_BEHAVIORS[CharacterType.SUPPORTING]
    )

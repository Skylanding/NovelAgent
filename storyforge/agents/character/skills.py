"""Skill system with scene-based triggers and matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from storyforge.agents.character.sheet import Skill


class SceneType(str, Enum):
    """Scene types that can trigger character skills."""

    COMBAT = "combat"
    NEGOTIATION = "negotiation"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    INVESTIGATION = "investigation"
    STEALTH = "stealth"
    SURVIVAL = "survival"
    MAGIC = "magic"
    EMOTIONAL = "emotional"


@dataclass
class SkillActivation:
    """Record of a skill being activated in a scene."""

    skill_name: str
    scene_type: SceneType
    chapter_number: int
    scene_index: int
    effectiveness: int = 5
    """1-10, how well the skill worked."""

    narrative_impact: str = ""
    """Description of what happened when skill was used."""


class SkillMatcher:
    """Matches character skills to scene requirements."""

    # Mapping of scene types to skill keywords
    SKILL_KEYWORDS: dict[SceneType, list[str]] = {
        SceneType.COMBAT: [
            "fight",
            "combat",
            "battle",
            "attack",
            "defend",
            "weapon",
            "martial",
            "archer",
            "archery",
            "sword",
            "war",
            "duel",
            "warrior",
            "soldier",
            "strike",
            "parry",
            "shield",
        ],
        SceneType.NEGOTIATION: [
            "negotiate",
            "bargain",
            "persuade",
            "diplomat",
            "trade",
            "convince",
            "deal",
            "merchant",
            "parley",
            "treaty",
            "agreement",
            "commerce",
        ],
        SceneType.EXPLORATION: [
            "explore",
            "navigate",
            "track",
            "wilderness",
            "survival",
            "scout",
            "map",
            "terrain",
            "journey",
            "travel",
            "path",
            "trail",
            "hunter",
            "ranger",
        ],
        SceneType.SOCIAL: [
            "social",
            "charm",
            "deception",
            "etiquette",
            "court",
            "gossip",
            "influence",
            "reputation",
            "perform",
            "dance",
            "noble",
            "politics",
        ],
        SceneType.INVESTIGATION: [
            "investigate",
            "detect",
            "analyze",
            "observe",
            "deduce",
            "research",
            "lore",
            "knowledge",
            "scholar",
            "clue",
            "mystery",
            "examine",
        ],
        SceneType.STEALTH: [
            "stealth",
            "sneak",
            "hide",
            "shadow",
            "infiltrate",
            "lockpick",
            "thief",
            "spy",
            "covert",
            "silent",
            "unseen",
            "assassin",
        ],
        SceneType.SURVIVAL: [
            "survival",
            "endurance",
            "heal",
            "forage",
            "shelter",
            "weather",
            "poison",
            "nature",
            "camp",
            "food",
            "water",
            "medicine",
        ],
        SceneType.MAGIC: [
            "magic",
            "spell",
            "aether",
            "arcane",
            "ritual",
            "enchant",
            "conjure",
            "shard",
            "void",
            "mystical",
            "supernatural",
            "power",
            "energy",
        ],
        SceneType.EMOTIONAL: [
            "comfort",
            "console",
            "empathy",
            "emotion",
            "feeling",
            "heart",
            "understand",
            "support",
            "grief",
            "love",
            "fear",
            "anger",
        ],
    }

    @classmethod
    def detect_scene_type(cls, scene_plan: dict[str, Any]) -> list[SceneType]:
        """Detect scene types from scene plan content."""
        # Combine relevant text fields
        text_parts = [
            str(scene_plan.get("scene_goal", "")),
            str(scene_plan.get("conflict", "")),
            str(scene_plan.get("location", "")),
            str(scene_plan.get("expected_outcome", "")),
        ]
        beats = scene_plan.get("beats", [])
        if isinstance(beats, list):
            text_parts.extend(str(b) for b in beats)

        text = " ".join(text_parts).lower()

        detected: list[SceneType] = []
        for scene_type, keywords in cls.SKILL_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                detected.append(scene_type)

        # Default to social if no specific type detected
        return detected or [SceneType.SOCIAL]

    @classmethod
    def get_relevant_skills(
        cls,
        skills: list["Skill"],
        scene_types: list[SceneType],
    ) -> list["Skill"]:
        """Find skills relevant to the detected scene types."""
        relevant: list["Skill"] = []
        scene_type_values = {st.value for st in scene_types}

        for skill in skills:
            # Check explicit triggers first
            if skill.scene_triggers:
                if any(t in scene_type_values for t in skill.scene_triggers):
                    relevant.append(skill)
                    continue

            # Check keyword matching in skill name/description
            skill_text = f"{skill.name} {skill.description}".lower()
            for scene_type in scene_types:
                keywords = cls.SKILL_KEYWORDS.get(scene_type, [])
                if any(kw in skill_text for kw in keywords):
                    relevant.append(skill)
                    break

        return relevant

    @classmethod
    def rank_skills_for_scene(
        cls,
        skills: list["Skill"],
        scene_types: list[SceneType],
    ) -> list[tuple["Skill", float]]:
        """
        Rank skills by relevance to the scene.
        Returns list of (skill, relevance_score) tuples, sorted by score descending.
        """
        scored: list[tuple["Skill", float]] = []
        scene_type_values = {st.value for st in scene_types}

        for skill in skills:
            score = 0.0

            # Explicit trigger match is highest weight
            if skill.scene_triggers:
                matches = sum(1 for t in skill.scene_triggers if t in scene_type_values)
                score += matches * 2.0

            # Keyword matching
            skill_text = f"{skill.name} {skill.description}".lower()
            for scene_type in scene_types:
                keywords = cls.SKILL_KEYWORDS.get(scene_type, [])
                keyword_matches = sum(1 for kw in keywords if kw in skill_text)
                score += keyword_matches * 0.5

            # Proficiency level as tiebreaker
            score += skill.proficiency_level * 0.1

            if score > 0:
                scored.append((skill, score))

        return sorted(scored, key=lambda x: x[1], reverse=True)

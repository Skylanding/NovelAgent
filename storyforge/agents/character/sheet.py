"""Enhanced character sheet with skills, relationships, and emotional state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from storyforge.agents.character.types import CharacterType, NarrativeWeight


@dataclass
class Skill:
    """A character skill with scene triggers."""

    name: str
    description: str = ""
    proficiency_level: int = 5
    """1-10 scale of skill mastery."""

    scene_triggers: list[str] = field(default_factory=list)
    """Scene types that activate this skill (e.g., ['combat', 'exploration'])."""

    cooldown_scenes: int = 0
    """Scenes before skill can be highlighted again (0 = no cooldown)."""

    last_used_scene: Optional[int] = None
    """Track when skill was last prominently used."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Skill":
        """Create a Skill from a dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            proficiency_level=data.get("proficiency_level", 5),
            scene_triggers=data.get("scene_triggers", []),
            cooldown_scenes=data.get("cooldown_scenes", 0),
        )

    @classmethod
    def from_string(cls, skill_str: str) -> "Skill":
        """Create a basic Skill from a legacy string format."""
        return cls(
            name=skill_str,
            description=skill_str,
            proficiency_level=5,
            scene_triggers=[],
        )


@dataclass
class RelationshipState:
    """Dynamic relationship with another character."""

    target_character: str
    relationship_type: str = "neutral"
    """ally, rival, mentor-student, romantic, hostile, neutral, familial, etc."""

    trust_level: int = 0
    """-10 to +10 scale."""

    history: list[str] = field(default_factory=list)
    """Key events in this relationship."""

    current_tension: str = ""
    """Active conflict or bond being explored."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RelationshipState":
        """Create a RelationshipState from a dictionary."""
        return cls(
            target_character=data.get("target_character", "Unknown"),
            relationship_type=data.get("relationship_type", "neutral"),
            trust_level=data.get("trust_level", 0),
            history=data.get("history", []),
            current_tension=data.get("current_tension", ""),
        )

    @classmethod
    def from_legacy(cls, name: str, description: str) -> "RelationshipState":
        """Create from legacy dict[str, str] format."""
        return cls(
            target_character=name,
            relationship_type="complex",
            trust_level=0,
            history=[description] if description else [],
            current_tension="",
        )


@dataclass
class EmotionalState:
    """Character's current emotional state with transition history."""

    current_state: str = "neutral"
    intensity: int = 5
    """1-10 scale of emotional intensity."""

    trigger_event: str = ""
    """What caused the current state."""

    previous_states: list[str] = field(default_factory=list)
    """Recent emotional states for tracking trajectory."""

    state_duration: int = 0
    """Scenes spent in current state."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmotionalState":
        """Create an EmotionalState from a dictionary."""
        return cls(
            current_state=data.get("current_state", "neutral"),
            intensity=data.get("intensity", 5),
            trigger_event=data.get("trigger_event", ""),
            previous_states=data.get("previous_states", []),
            state_duration=data.get("state_duration", 0),
        )

    @classmethod
    def from_string(cls, state_str: str) -> "EmotionalState":
        """Create from legacy string format."""
        return cls(current_state=state_str, intensity=5)


@dataclass
class EnhancedCharacterSheet:
    """Extended character definition with types, skills, relationships, and emotional state."""

    # Core identity (backward compatible with original CharacterSheet)
    name: str
    age: int = 0
    personality_traits: list[str] = field(default_factory=list)
    backstory: str = ""
    motivations: list[str] = field(default_factory=list)
    speech_patterns: str = ""
    appearance: str = ""
    arc_summary: str = ""

    # Character type classification
    character_type: CharacterType = CharacterType.SUPPORTING
    narrative_weight: Optional[NarrativeWeight] = None
    """Optional override of type's default narrative weight."""

    # Skills system
    skills: list[Skill] = field(default_factory=list)

    # Relationships (dynamic)
    relationships: list[RelationshipState] = field(default_factory=list)

    # Emotional state machine
    emotional_state: EmotionalState = field(default_factory=EmotionalState)

    # Legacy compatibility fields (for preserving original data)
    _legacy_relationships: dict[str, str] = field(default_factory=dict)
    _legacy_emotional_state: str = ""
    _legacy_skills: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnhancedCharacterSheet":
        """
        Parse from YAML/dict with full backward compatibility.
        Handles both legacy and new formats automatically.
        """
        sheet = cls(
            name=data.get("name", "Unknown"),
            age=data.get("age", 0),
            personality_traits=data.get("personality_traits", []),
            backstory=data.get("backstory", ""),
            motivations=data.get("motivations", []),
            speech_patterns=data.get("speech_patterns", ""),
            appearance=data.get("appearance", ""),
            arc_summary=data.get("arc_summary", ""),
        )

        # Parse character type (new field, defaults to SUPPORTING)
        if "character_type" in data:
            try:
                sheet.character_type = CharacterType(data["character_type"])
            except ValueError:
                sheet.character_type = CharacterType.SUPPORTING

        # Parse narrative weight override
        if "narrative_weight" in data:
            nw = data["narrative_weight"]
            sheet.narrative_weight = NarrativeWeight(
                dialogue_ratio=nw.get("dialogue_ratio", 1.0),
                internal_monologue_depth=nw.get("internal_monologue_depth", 3),
                scene_presence_priority=nw.get("scene_presence_priority", 5),
                reaction_detail_level=nw.get("reaction_detail_level", 3),
            )

        # Parse skills - support both legacy list[str] and new Skill format
        raw_skills = data.get("skills", [])
        if raw_skills:
            if isinstance(raw_skills[0], str):
                # Legacy format: list of strings
                sheet._legacy_skills = raw_skills
                sheet.skills = [Skill.from_string(s) for s in raw_skills]
            elif isinstance(raw_skills[0], dict):
                # New format: list of Skill dicts
                sheet.skills = [Skill.from_dict(s) for s in raw_skills]
            else:
                sheet.skills = []

        # Parse relationships - support both legacy dict and new RelationshipState
        raw_rels = data.get("relationships", {})
        if isinstance(raw_rels, dict):
            # Legacy format: dict[str, str]
            sheet._legacy_relationships = raw_rels
            sheet.relationships = [
                RelationshipState.from_legacy(k, v) for k, v in raw_rels.items()
            ]
        elif isinstance(raw_rels, list):
            # New format: list of RelationshipState dicts
            sheet.relationships = [RelationshipState.from_dict(r) for r in raw_rels]
        else:
            sheet.relationships = []

        # Parse emotional state - support both string and dict formats
        raw_emotion = data.get("emotional_state", "neutral")
        if isinstance(raw_emotion, str):
            # Legacy format: simple string
            sheet._legacy_emotional_state = raw_emotion
            sheet.emotional_state = EmotionalState.from_string(raw_emotion)
        elif isinstance(raw_emotion, dict):
            # New format: EmotionalState dict
            sheet.emotional_state = EmotionalState.from_dict(raw_emotion)
        else:
            sheet.emotional_state = EmotionalState()

        return sheet

    def to_prompt_text(self) -> str:
        """Serialize to a prompt-friendly text format (enhanced version)."""
        lines = [
            f"Name: {self.name}",
            f"Type: {self.character_type.value.replace('_', ' ').title()}",
        ]

        if self.age:
            lines.append(f"Age: {self.age}")
        if self.personality_traits:
            lines.append(f"Personality: {', '.join(self.personality_traits)}")
        if self.backstory:
            lines.append(f"Backstory: {self.backstory}")
        if self.motivations:
            lines.append(f"Motivations: {', '.join(self.motivations)}")
        if self.speech_patterns:
            lines.append(f"Speech patterns: {self.speech_patterns}")

        lines.append(
            f"Current emotional state: {self.emotional_state.current_state} "
            f"(intensity: {self.emotional_state.intensity}/10)"
        )

        if self.appearance:
            lines.append(f"Appearance: {self.appearance}")

        # Skills section
        if self.skills:
            skill_lines = []
            for s in self.skills:
                skill_line = f"  - {s.name}"
                if s.proficiency_level != 5:
                    skill_line += f" (level {s.proficiency_level}/10)"
                if s.description and s.description != s.name:
                    skill_line += f": {s.description}"
                skill_lines.append(skill_line)
            lines.append("Skills:\n" + "\n".join(skill_lines))

        # Relationships section
        if self.relationships:
            rel_lines = []
            for r in self.relationships:
                rel_line = f"  - {r.target_character}: {r.relationship_type}"
                if r.trust_level != 0:
                    rel_line += f" (trust: {r.trust_level:+d})"
                rel_lines.append(rel_line)
            lines.append("Relationships:\n" + "\n".join(rel_lines))

        if self.arc_summary:
            lines.append(f"Character arc: {self.arc_summary}")

        return "\n".join(line for line in lines if line)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary format."""
        return {
            "name": self.name,
            "age": self.age,
            "character_type": self.character_type.value,
            "personality_traits": self.personality_traits,
            "backstory": self.backstory,
            "motivations": self.motivations,
            "speech_patterns": self.speech_patterns,
            "appearance": self.appearance,
            "arc_summary": self.arc_summary,
            "skills": [
                {
                    "name": s.name,
                    "description": s.description,
                    "proficiency_level": s.proficiency_level,
                    "scene_triggers": s.scene_triggers,
                }
                for s in self.skills
            ],
            "relationships": [
                {
                    "target_character": r.target_character,
                    "relationship_type": r.relationship_type,
                    "trust_level": r.trust_level,
                    "history": r.history,
                    "current_tension": r.current_tension,
                }
                for r in self.relationships
            ],
            "emotional_state": {
                "current_state": self.emotional_state.current_state,
                "intensity": self.emotional_state.intensity,
                "trigger_event": self.emotional_state.trigger_event,
                "previous_states": self.emotional_state.previous_states,
            },
        }

    def get_relationship(self, target: str) -> Optional[RelationshipState]:
        """Get relationship with a specific character."""
        for rel in self.relationships:
            if rel.target_character.lower() == target.lower():
                return rel
        return None

    def get_skills_for_scene_types(self, scene_types: list[str]) -> list[Skill]:
        """Get skills relevant to given scene types."""
        relevant = []
        for skill in self.skills:
            if skill.scene_triggers:
                if any(st in skill.scene_triggers for st in scene_types):
                    relevant.append(skill)
        return relevant


# Backward compatibility alias
CharacterSheet = EnhancedCharacterSheet

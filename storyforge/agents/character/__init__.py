"""Enhanced character agent module with type classification, skills, and constraints."""

from storyforge.agents.character.types import (
    CharacterType,
    NarrativeWeight,
    TypeBehavior,
    TYPE_BEHAVIORS,
)
from storyforge.agents.character.sheet import (
    EnhancedCharacterSheet,
    Skill,
    RelationshipState,
    EmotionalState,
)
from storyforge.agents.character.skills import (
    SceneType,
    SkillActivation,
    SkillMatcher,
)
from storyforge.agents.character.relationships import (
    RelationshipType,
    RelationshipModifier,
    RelationshipManager,
)
from storyforge.agents.character.emotional_state import (
    EmotionCategory,
    EmotionalTransition,
    EmotionalStateMachine,
)
from storyforge.agents.character.constraints import (
    BehaviorConstraint,
    ConstraintEngine,
)
from storyforge.agents.character.agent import EnhancedCharacterAgent

# Re-export for backward compatibility
CharacterAgent = EnhancedCharacterAgent
CharacterSheet = EnhancedCharacterSheet

__all__ = [
    # Types
    "CharacterType",
    "NarrativeWeight",
    "TypeBehavior",
    "TYPE_BEHAVIORS",
    # Sheet
    "EnhancedCharacterSheet",
    "Skill",
    "RelationshipState",
    "EmotionalState",
    # Skills
    "SceneType",
    "SkillActivation",
    "SkillMatcher",
    # Relationships
    "RelationshipType",
    "RelationshipModifier",
    "RelationshipManager",
    # Emotional State
    "EmotionCategory",
    "EmotionalTransition",
    "EmotionalStateMachine",
    # Constraints
    "BehaviorConstraint",
    "ConstraintEngine",
    # Agent
    "EnhancedCharacterAgent",
    "CharacterAgent",
    "CharacterSheet",
]

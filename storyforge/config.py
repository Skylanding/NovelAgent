"""Configuration loading and validation for StoryForge projects."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class LLMBackendConfig(BaseModel):
    """Configuration for a single LLM backend."""

    provider: str  # "ollama", "anthropic", "openai"
    model: str  # e.g. "llama3.1:8b", "claude-sonnet-4-20250514"
    tier: str  # "small", "medium", "large"
    api_key_env: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    context_window: int = 8192
    requests_per_minute: int = 60
    default_temperature: float = 0.7

    @model_validator(mode="after")
    def resolve_api_key(self) -> "LLMBackendConfig":
        if self.api_key is None and self.api_key_env:
            self.api_key = os.environ.get(self.api_key_env)
            if self.api_key is None:
                import logging
                logging.getLogger(__name__).warning(
                    "Environment variable %s is not set for provider %s/%s",
                    self.api_key_env, self.provider, self.model,
                )
        return self


class SkillConfig(BaseModel):
    """Configuration for a character skill."""

    name: str
    description: str = ""
    proficiency_level: int = 5
    scene_triggers: list[str] = Field(default_factory=list)


class RelationshipConfig(BaseModel):
    """Configuration for a character relationship."""

    target_character: str
    relationship_type: str = "neutral"
    trust_level: int = 0
    initial_history: list[str] = Field(default_factory=list)
    current_tension: str = ""


class EmotionalStateConfig(BaseModel):
    """Configuration for initial emotional state."""

    current_state: str = "neutral"
    intensity: int = 5
    trigger_event: str = ""


class NarrativeWeightConfig(BaseModel):
    """Configuration for narrative weight overrides."""

    dialogue_ratio: Optional[float] = None
    internal_monologue_depth: Optional[int] = None
    scene_presence_priority: Optional[int] = None
    reaction_detail_level: Optional[int] = None


class CharacterAgentConfig(BaseModel):
    """Configuration for a character agent."""

    name: str
    llm_backend: str
    system_prompt: str = "prompts/character/system.jinja2"
    character_sheet: str
    memory_type: str = "vector"
    memory_path: str = ""

    # Character type classification
    character_type: str = "supporting"
    """protagonist, antagonist, mentor, sidekick, threshold_guardian, supporting"""

    # Optional narrative weight overrides
    narrative_weight: Optional[NarrativeWeightConfig] = None

    # Additional skills (merged with character sheet skills)
    additional_skills: list[SkillConfig] = Field(default_factory=list)

    # Relationship overrides (merged with character sheet relationships)
    relationship_overrides: list[RelationshipConfig] = Field(default_factory=list)

    # Initial emotional state override
    initial_emotional_state: Optional[EmotionalStateConfig] = None


class AgentsConfig(BaseModel):
    """Configuration for all agent assignments."""

    world: dict[str, Any]
    plot: dict[str, Any]
    writing: dict[str, Any]
    characters: list[CharacterAgentConfig] = Field(default_factory=list)


class PipelineConfig(BaseModel):
    """Pipeline execution settings."""

    max_revision_rounds: int = 3
    scene_composition_timeout: int = 180
    character_reaction_timeout: int = 60
    parallel_character_reactions: bool = True


class OutputConfig(BaseModel):
    """Output and export settings."""

    directory: str = "output/"
    formats: list[str] = Field(default_factory=lambda: ["markdown"])
    versioning: bool = True
    save_intermediates: bool = True


class ProjectMeta(BaseModel):
    """Project metadata."""

    name: str
    author: str = "StoryForge"
    genre: str = ""
    language: str = "English"
    target_word_count: int = 50000
    target_chapters: int = 12


class ProjectConfig(BaseModel):
    """Root configuration model for a StoryForge project."""

    project: ProjectMeta
    llm_backends: dict[str, LLMBackendConfig]
    agents: AgentsConfig
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    world: dict[str, Any] = Field(default_factory=dict)
    plot: dict[str, Any] = Field(default_factory=dict)


def load_config(project_dir: Path) -> ProjectConfig:
    """Load and validate a project configuration from a directory."""
    config_path = project_dir / "project.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Project config not found: {config_path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    return ProjectConfig(**raw)


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}

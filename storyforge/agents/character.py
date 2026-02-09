"""CharacterAgent — embodies a single character's personality and memory."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from storyforge.agents.base import AgentConfig, BaseAgent
from storyforge.agents.registry import AgentRegistry
from storyforge.events.bus import EventBus
from storyforge.events.types import Event, EventType
from storyforge.llm.base import LLMBackend
from storyforge.memory.base import MemoryStore

logger = logging.getLogger(__name__)


@dataclass
class CharacterSheet:
    """Structured character definition."""

    name: str
    age: int = 0
    personality_traits: list[str] = field(default_factory=list)
    backstory: str = ""
    motivations: list[str] = field(default_factory=list)
    speech_patterns: str = ""
    relationships: dict[str, str] = field(default_factory=dict)
    emotional_state: str = "neutral"
    arc_summary: str = ""
    appearance: str = ""
    skills: list[str] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        """Serialize to a compact text format for prompts."""
        lines = [
            f"Name: {self.name}",
            f"Age: {self.age}" if self.age else "",
            f"Personality: {', '.join(self.personality_traits)}" if self.personality_traits else "",
            f"Backstory: {self.backstory}" if self.backstory else "",
            f"Motivations: {', '.join(self.motivations)}" if self.motivations else "",
            f"Speech patterns: {self.speech_patterns}" if self.speech_patterns else "",
            f"Current emotional state: {self.emotional_state}",
            f"Appearance: {self.appearance}" if self.appearance else "",
        ]
        if self.relationships:
            rel_lines = [f"  - {k}: {v}" for k, v in self.relationships.items()]
            lines.append("Relationships:\n" + "\n".join(rel_lines))
        if self.arc_summary:
            lines.append(f"Character arc: {self.arc_summary}")
        return "\n".join(line for line in lines if line)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterSheet":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CharacterReaction:
    """A character's reaction to a scene."""

    character_name: str
    internal_thoughts: str
    emotional_shift: str
    desired_actions: list[str]
    body_language: str = ""


@dataclass
class DialogueLine:
    """A single line of dialogue."""

    character_name: str
    text: str
    tone: str = ""
    action: str = ""  # accompanying action/gesture


@AgentRegistry.register("character")
class CharacterAgent(BaseAgent):
    """Embodies a single character — personality, memory, dialogue."""

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMBackend,
        memory: MemoryStore,
        event_bus: EventBus,
        character_sheet: CharacterSheet,
        prompt_dir: Optional[Path] = None,
    ) -> None:
        super().__init__(config, llm, memory, event_bus, prompt_dir)
        self.character_sheet = character_sheet
        self._system_prompt = self._build_character_system_prompt()

    async def handle_event(self, event: Event) -> Optional[Event]:
        handlers = {
            EventType.CHARACTER_REACTION_REQUEST: self._handle_reaction,
            EventType.DIALOGUE_REQUEST: self._handle_dialogue,
        }
        handler = handlers.get(event.event_type)
        if handler:
            return await handler(event)
        return None

    async def _handle_reaction(self, event: Event) -> Event:
        scene_plan = event.payload.get("scene_plan", {})
        setting = event.payload.get("setting", {})
        reaction = await self.react_to_scene(scene_plan, setting)
        return event.create_response(
            EventType.CHARACTER_REACTION,
            {"reaction": {
                "character_name": reaction.character_name,
                "internal_thoughts": reaction.internal_thoughts,
                "emotional_shift": reaction.emotional_shift,
                "desired_actions": reaction.desired_actions,
                "body_language": reaction.body_language,
            }},
            self.config.name,
        )

    async def _handle_dialogue(self, event: Event) -> Event:
        beat = event.payload.get("beat", "")
        previous = event.payload.get("previous_dialogue", [])
        scene_context = event.payload.get("scene_context", {})
        line = await self.generate_dialogue(beat, previous, scene_context)
        return event.create_response(
            EventType.DIALOGUE_RESPONSE,
            {"dialogue": {
                "character_name": line.character_name,
                "text": line.text,
                "tone": line.tone,
                "action": line.action,
            }},
            self.config.name,
        )

    async def react_to_scene(
        self,
        scene_plan: dict[str, Any],
        setting: dict[str, Any],
    ) -> CharacterReaction:
        """Generate character's reaction to a scene."""
        memories = await self._get_relevant_memories(
            str(scene_plan.get("scene_goal", ""))
        )
        memory_text = "\n".join(
            f"- {m.get('content', m)}" for m in memories
        ) if memories else "No relevant memories."

        prompt = f"""You are {self.character_sheet.name}. React to this scene IN CHARACTER.

Scene:
- Location: {scene_plan.get('location', 'unknown')}
- Characters present: {scene_plan.get('characters_present', [])}
- What's happening: {scene_plan.get('scene_goal', '')}
- Conflict: {scene_plan.get('conflict', '')}

Setting details: {json.dumps(setting.get('setting_details', ''), ensure_ascii=False) if isinstance(setting, dict) else setting}

Your relevant memories:
{memory_text}

Respond as JSON:
{{
    "internal_thoughts": "what you're thinking and feeling",
    "emotional_shift": "how your emotional state changes (e.g., 'anxious -> determined')",
    "desired_actions": ["what you want to do in this scene"],
    "body_language": "your physical reactions and body language"
}}"""
        response = await self.generate(prompt, temperature=0.8)
        try:
            data = json.loads(response)
            return CharacterReaction(
                character_name=self.character_sheet.name,
                internal_thoughts=data.get("internal_thoughts", ""),
                emotional_shift=data.get("emotional_shift", ""),
                desired_actions=data.get("desired_actions", []),
                body_language=data.get("body_language", ""),
            )
        except json.JSONDecodeError:
            return CharacterReaction(
                character_name=self.character_sheet.name,
                internal_thoughts=response,
                emotional_shift="unchanged",
                desired_actions=[],
                body_language="",
            )

    async def generate_dialogue(
        self,
        beat: str,
        previous_dialogue: list[dict[str, Any]],
        scene_context: dict[str, Any],
    ) -> DialogueLine:
        """Generate a dialogue line in the character's voice."""
        prev_text = ""
        if previous_dialogue:
            prev_lines = [
                f'{d.get("character_name", "?")}: "{d.get("text", "")}"'
                for d in previous_dialogue[-4:]
            ]
            prev_text = "\n".join(prev_lines)

        dialogue_section = f"Previous dialogue:\n{prev_text}" if prev_text else "This is the start of the conversation."
        prompt = f"""You are {self.character_sheet.name}. Speak in character.

Current beat: {beat}
Scene context: {scene_context.get('scene_goal', '')}

{dialogue_section}

Generate ONE line of dialogue as {self.character_sheet.name}. Stay in character.
Respond as JSON:
{{
    "text": "the dialogue line",
    "tone": "emotional tone of delivery",
    "action": "accompanying physical action or gesture"
}}"""
        response = await self.generate(prompt, temperature=0.85)
        try:
            data = json.loads(response)
            return DialogueLine(
                character_name=self.character_sheet.name,
                text=data.get("text", ""),
                tone=data.get("tone", ""),
                action=data.get("action", ""),
            )
        except json.JSONDecodeError:
            return DialogueLine(
                character_name=self.character_sheet.name,
                text=response.strip('"'),
                tone="neutral",
                action="",
            )

    async def update_emotional_state(self, events: list[str]) -> None:
        """Update character's emotional state based on what happened."""
        events_text = "\n".join(f"- {e}" for e in events)
        prompt = (
            f"You are {self.character_sheet.name}.\n"
            f"Current emotional state: {self.character_sheet.emotional_state}\n\n"
            f"These events just happened:\n{events_text}\n\n"
            "What is your new emotional state? Respond with a brief description (2-5 words)."
        )
        new_state = await self.generate(prompt, temperature=0.6)
        self.character_sheet.emotional_state = new_state.strip()

    async def _get_relevant_memories(
        self, context: str, top_k: int = 5
    ) -> list[dict]:
        """Retrieve relevant memories for the current scene."""
        try:
            return await self.memory.search(context, top_k=top_k)
        except Exception:
            return []

    def _build_character_system_prompt(self) -> str:
        """Build the system prompt incorporating the character sheet."""
        return f"""You are roleplaying as {self.character_sheet.name}, a character in a novel.

CHARACTER SHEET:
{self.character_sheet.to_prompt_text()}

RULES:
- Always respond in character as {self.character_sheet.name}
- Maintain consistent personality, speech patterns, and motivations
- Your responses should reflect your emotional state and relationships
- When generating dialogue, use speech patterns defined in your character sheet
- React authentically based on your backstory and current emotional state"""

"""Enhanced CharacterAgent with type classification, skills, and constraints."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from storyforge.agents.base import AgentConfig, BaseAgent, strip_json_fences
from storyforge.agents.registry import AgentRegistry
from storyforge.agents.character.types import (
    CharacterType,
    TypeBehavior,
    TYPE_BEHAVIORS,
    get_type_behavior,
)
from storyforge.agents.character.sheet import EnhancedCharacterSheet
from storyforge.agents.character.skills import SkillMatcher, SceneType
from storyforge.agents.character.relationships import RelationshipManager
from storyforge.agents.character.emotional_state import EmotionalStateMachine
from storyforge.agents.character.constraints import ConstraintEngine
from storyforge.events.bus import EventBus
from storyforge.events.types import Event, EventType
from storyforge.llm.base import LLMBackend
from storyforge.memory.base import MemoryStore

logger = logging.getLogger(__name__)


@AgentRegistry.register("character")
class EnhancedCharacterAgent(BaseAgent):
    """Character agent with type-aware behavior, skills, relationships, and constraints."""

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMBackend,
        memory: MemoryStore,
        event_bus: EventBus,
        character_sheet: EnhancedCharacterSheet,
        prompt_dir: Optional[Path] = None,
    ) -> None:
        super().__init__(config, llm, memory, event_bus, prompt_dir)
        self.character_sheet = character_sheet
        self.type_behavior = get_type_behavior(character_sheet.character_type)
        self.emotional_machine = EmotionalStateMachine(
            character_sheet.character_type.value
        )
        self._system_prompt = self._build_character_system_prompt()

    async def handle_event(self, event: Event) -> Optional[Event]:
        """Handle events with type-aware processing."""
        handlers = {
            EventType.CHARACTER_REACTION_REQUEST: self._handle_reaction,
            EventType.DIALOGUE_REQUEST: self._handle_dialogue,
        }
        handler = handlers.get(event.event_type)
        if handler:
            return await handler(event)
        return None

    async def _handle_reaction(self, event: Event) -> Event:
        """Generate type-aware character reaction."""
        scene_plan = event.payload.get("scene_plan", {})
        setting = event.payload.get("setting", {})

        # Detect scene type and get relevant skills
        scene_types = SkillMatcher.detect_scene_type(scene_plan)
        active_skills = SkillMatcher.get_relevant_skills(
            self.character_sheet.skills, scene_types
        )

        # Get relationship context for characters present
        relationship_contexts = self._get_relationship_contexts(
            scene_plan.get("characters_present", []), scene_plan
        )

        reaction = await self.react_to_scene(
            scene_plan, setting, active_skills, relationship_contexts
        )

        return event.create_response(
            EventType.CHARACTER_REACTION,
            {"reaction": reaction},
            self.config.name,
        )

    async def _handle_dialogue(self, event: Event) -> Event:
        """Generate dialogue with relationship and type awareness."""
        beat = event.payload.get("beat", "")
        previous = event.payload.get("previous_dialogue", [])
        scene_context = event.payload.get("scene_context", {})

        # Get relationship contexts for dialogue partners
        characters_in_dialogue = set()
        for d in previous:
            if d.get("character_name"):
                characters_in_dialogue.add(d["character_name"])

        relationship_contexts = self._get_relationship_contexts(
            list(characters_in_dialogue), scene_context
        )

        line = await self.generate_dialogue(
            beat, previous, scene_context, relationship_contexts
        )

        return event.create_response(
            EventType.DIALOGUE_RESPONSE,
            {
                "dialogue": {
                    "character_name": line["character_name"],
                    "text": line["text"],
                    "tone": line["tone"],
                    "action": line["action"],
                }
            },
            self.config.name,
        )

    async def react_to_scene(
        self,
        scene_plan: dict[str, Any],
        setting: dict[str, Any],
        active_skills: list,
        relationship_contexts: dict[str, dict],
    ) -> dict[str, Any]:
        """Generate enhanced reaction with skills and relationships."""
        memories = await self._get_relevant_memories(
            str(scene_plan.get("scene_goal", ""))
        )
        memory_text = (
            "\n".join(f"- {m.get('content', m)}" for m in memories)
            if memories
            else "No relevant memories."
        )

        # Build skills section
        skills_text = ""
        if active_skills:
            skill_lines = [
                f"- {s.name} (level {s.proficiency_level}/10): {s.description}"
                for s in active_skills
            ]
            skills_text = "ACTIVE SKILLS FOR THIS SCENE:\n" + "\n".join(skill_lines)

        # Build relationships section
        rel_text = ""
        if relationship_contexts:
            rel_parts = []
            for char_name, ctx in relationship_contexts.items():
                rel_parts.append(
                    f"- {char_name}: {ctx['tone']} "
                    f"(help likelihood: {ctx['help_likelihood']:.0%})"
                )
            rel_text = "RELATIONSHIP DYNAMICS:\n" + "\n".join(rel_parts)

        # Get behavior constraints
        constraints_text = ConstraintEngine.build_constraint_prompt(
            self.character_sheet.character_type
        )

        # Get emotional state info
        emotional_info = self.emotional_machine.format_for_prompt(
            self.character_sheet.emotional_state.current_state,
            self.character_sheet.emotional_state.intensity,
            self.character_sheet.emotional_state.previous_states,
        )

        # Build setting text
        setting_text = ""
        if isinstance(setting, dict):
            setting_details = setting.get("setting_details", "")
            if setting_details:
                setting_text = json.dumps(setting_details, ensure_ascii=False)

        prompt = f"""You are {self.character_sheet.name}. React to this scene IN CHARACTER.

CHARACTER TYPE: {self.character_sheet.character_type.value.replace('_', ' ').title()}

{constraints_text}

Scene:
- Location: {scene_plan.get('location', 'unknown')}
- Characters present: {scene_plan.get('characters_present', [])}
- What's happening: {scene_plan.get('scene_goal', '')}
- Conflict: {scene_plan.get('conflict', '')}

Setting details: {setting_text}

{emotional_info}

{skills_text}

{rel_text}

Your relevant memories:
{memory_text}

Respond as JSON:
{{
    "internal_thoughts": "what you're thinking and feeling (depth based on your type)",
    "emotional_shift": "how your emotional state changes (e.g., 'anxious -> determined')",
    "desired_actions": ["what you want to do in this scene, respecting your type constraints"],
    "body_language": "your physical reactions and body language",
    "skill_application": "which of your active skills you might use and how (if any)"
}}"""

        response = await self.generate(prompt, temperature=0.8)
        try:
            data = json.loads(strip_json_fences(response))

            # Update emotional state if shift occurred
            if data.get("emotional_shift"):
                await self._process_emotional_shift(data["emotional_shift"])

            return {
                "character_name": self.character_sheet.name,
                "character_type": self.character_sheet.character_type.value,
                "internal_thoughts": data.get("internal_thoughts", ""),
                "emotional_shift": data.get("emotional_shift", ""),
                "desired_actions": data.get("desired_actions", []),
                "body_language": data.get("body_language", ""),
                "skill_application": data.get("skill_application", ""),
            }
        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse reaction JSON for {self.character_sheet.name}"
            )
            return {
                "character_name": self.character_sheet.name,
                "character_type": self.character_sheet.character_type.value,
                "internal_thoughts": response,
                "emotional_shift": "unchanged",
                "desired_actions": [],
                "body_language": "",
                "skill_application": "",
            }

    async def generate_dialogue(
        self,
        beat: str,
        previous_dialogue: list[dict[str, Any]],
        scene_context: dict[str, Any],
        relationship_contexts: dict[str, dict],
    ) -> dict[str, Any]:
        """Generate a dialogue line with type and relationship awareness."""
        # Format previous dialogue
        prev_text = ""
        if previous_dialogue:
            prev_lines = [
                f'{d.get("character_name", "?")}: "{d.get("text", "")}"'
                for d in previous_dialogue[-6:]
            ]
            prev_text = "\n".join(prev_lines)

        dialogue_section = (
            f"Previous dialogue:\n{prev_text}"
            if prev_text
            else "This is the start of the conversation."
        )

        # Build relationship context for dialogue
        rel_text = ""
        if relationship_contexts:
            rel_parts = []
            for char_name, ctx in relationship_contexts.items():
                rel_parts.append(
                    f"- With {char_name}: {ctx['formality']} tone, {ctx['tone']}"
                )
            rel_text = "DIALOGUE DYNAMICS:\n" + "\n".join(rel_parts)

        # Get constraints
        constraints_text = ConstraintEngine.build_constraint_prompt(
            self.character_sheet.character_type
        )

        prompt = f"""You are {self.character_sheet.name}. Speak in character.

CHARACTER TYPE: {self.character_sheet.character_type.value.replace('_', ' ').title()}
Speech patterns: {self.character_sheet.speech_patterns}

{constraints_text}

Current beat: {beat}
Scene context: {scene_context.get('scene_goal', '')}

{rel_text}

{dialogue_section}

Generate ONE line of dialogue as {self.character_sheet.name}. Stay in character.
Your dialogue should reflect your character type's role and constraints.

Respond as JSON:
{{
    "text": "the dialogue line",
    "tone": "emotional tone of delivery",
    "action": "accompanying physical action or gesture"
}}"""

        response = await self.generate(prompt, temperature=0.85)
        try:
            data = json.loads(strip_json_fences(response))
            return {
                "character_name": self.character_sheet.name,
                "text": data.get("text", ""),
                "tone": data.get("tone", ""),
                "action": data.get("action", ""),
            }
        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse dialogue JSON for {self.character_sheet.name}"
            )
            return {
                "character_name": self.character_sheet.name,
                "text": response.strip('"'),
                "tone": "neutral",
                "action": "",
            }

    async def update_emotional_state(self, events: list[str]) -> None:
        """Update character's emotional state based on what happened."""
        events_text = "\n".join(f"- {e}" for e in events)
        prompt = f"""You are {self.character_sheet.name}.
Current emotional state: {self.character_sheet.emotional_state.current_state}

These events just happened:
{events_text}

What is your new emotional state? Respond with a brief description (2-5 words)."""

        new_state = await self.generate(prompt, temperature=0.6)
        new_state = new_state.strip().lower()

        # Record the transition
        old_state = self.character_sheet.emotional_state.current_state
        self.emotional_machine.record_transition(
            from_state=old_state,
            to_state=new_state,
            trigger_type="events",
            trigger_description="; ".join(events[:3]),
        )

        self.character_sheet.emotional_state.previous_states.append(old_state)
        self.character_sheet.emotional_state.current_state = new_state

    def _get_relationship_contexts(
        self,
        characters_present: list[str],
        scene_context: dict[str, Any],
    ) -> dict[str, dict]:
        """Get relationship context for all characters in scene."""
        contexts = {}
        for rel in self.character_sheet.relationships:
            if rel.target_character in characters_present:
                contexts[rel.target_character] = (
                    RelationshipManager.compute_interaction_context(rel, scene_context)
                )
        return contexts

    async def _process_emotional_shift(self, shift_text: str) -> None:
        """Process and record emotional state transition."""
        parsed = self.emotional_machine.parse_emotional_shift(shift_text)
        if parsed:
            old_state, new_state = parsed

            self.emotional_machine.record_transition(
                from_state=old_state,
                to_state=new_state,
                trigger_type="scene",
                trigger_description=shift_text,
            )

            self.character_sheet.emotional_state.previous_states.append(old_state)
            self.character_sheet.emotional_state.current_state = new_state

    async def _get_relevant_memories(
        self, context: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Retrieve relevant memories for the current scene."""
        try:
            return await self.memory.search(context, top_k=top_k)
        except Exception as e:
            logger.debug(f"Memory search failed: {e}")
            return []

    def _build_character_system_prompt(self) -> str:
        """Build type-aware system prompt."""
        type_name = self.character_sheet.character_type.value.replace("_", " ").title()

        # Get constraints and actions
        constraints_text = ConstraintEngine.build_constraint_prompt(
            self.character_sheet.character_type
        )
        actions_text = ConstraintEngine.format_actions_for_prompt(
            self.character_sheet.character_type
        )

        base_prompt = f"""You are roleplaying as {self.character_sheet.name}, a character in a novel.

CHARACTER TYPE: {type_name}

CHARACTER SHEET:
{self.character_sheet.to_prompt_text()}

{constraints_text}

{actions_text}

RULES:
- Always respond in character as {self.character_sheet.name}
- Maintain consistent personality, speech patterns, and motivations
- Your responses should reflect your emotional state and relationships
- Respect your character type's narrative function and constraints
- When generating dialogue, use speech patterns defined in your character sheet
- React authentically based on your backstory and current emotional state
- Your internal thoughts should reveal your true feelings"""

        return base_prompt


# Backward compatibility - alias for the original class name
CharacterAgent = EnhancedCharacterAgent

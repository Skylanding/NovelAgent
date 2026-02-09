"""WritingAgent — produces polished prose from structured inputs."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from storyforge.agents.base import BaseAgent
from storyforge.agents.registry import AgentRegistry
from storyforge.events.types import Event, EventType

logger = logging.getLogger(__name__)


@AgentRegistry.register("writing")
class WritingAgent(BaseAgent):
    """Takes structured inputs and produces polished prose."""

    async def handle_event(self, event: Event) -> Optional[Event]:
        handlers = {
            EventType.SCENE_DRAFT_REQUEST: self._handle_scene_draft,
            EventType.REVISION_REQUEST: self._handle_revision,
        }
        handler = handlers.get(event.event_type)
        if handler:
            return await handler(event)
        return None

    async def _handle_scene_draft(self, event: Event) -> Event:
        scene_text = await self.compose_scene(
            scene_plan=event.payload.get("scene_plan", {}),
            character_reactions=event.payload.get("character_reactions", []),
            dialogue_lines=event.payload.get("dialogue_lines", []),
            setting=event.payload.get("setting", {}),
        )
        return event.create_response(
            EventType.SCENE_DRAFT_READY,
            {"scene_text": scene_text},
            self.config.name,
        )

    async def _handle_revision(self, event: Event) -> Event:
        revised = await self.revise(
            text=event.payload.get("chapter_text", ""),
            feedback=event.payload.get("feedback", []),
        )
        return event.create_response(
            EventType.REVISION_READY,
            {"revised_text": revised},
            self.config.name,
        )

    async def compose_scene(
        self,
        scene_plan: dict[str, Any],
        character_reactions: list[dict[str, Any]],
        dialogue_lines: list[dict[str, Any]],
        setting: dict[str, Any],
    ) -> str:
        """Compose a full scene from structured inputs."""
        # Format character reactions
        reactions_text = ""
        if character_reactions:
            parts = []
            for r in character_reactions:
                parts.append(
                    f"  {r.get('character_name', '?')}:\n"
                    f"    Thoughts: {r.get('internal_thoughts', '')}\n"
                    f"    Emotional shift: {r.get('emotional_shift', '')}\n"
                    f"    Actions: {r.get('desired_actions', [])}\n"
                    f"    Body language: {r.get('body_language', '')}"
                )
            reactions_text = "\n".join(parts)

        # Format dialogue
        dialogue_text = ""
        if dialogue_lines:
            parts = []
            for d in dialogue_lines:
                line = f'  {d.get("character_name", "?")}: "{d.get("text", "")}"'
                if d.get("tone"):
                    line += f" ({d['tone']})"
                if d.get("action"):
                    line += f" [{d['action']}]"
                parts.append(line)
            dialogue_text = "\n".join(parts)

        # Format setting
        setting_text = ""
        if isinstance(setting, dict):
            setting_text = json.dumps(
                {k: v for k, v in setting.items() if v},
                indent=2,
                ensure_ascii=False,
            )

        prompt = f"""Write a polished prose scene based on these inputs.

SCENE PLAN:
- Location: {scene_plan.get('location', 'unknown')}
- Characters: {scene_plan.get('characters_present', [])}
- Goal: {scene_plan.get('scene_goal', '')}
- Conflict: {scene_plan.get('conflict', '')}
- Expected outcome: {scene_plan.get('expected_outcome', '')}
- Beats: {scene_plan.get('beats', [])}
- POV: {scene_plan.get('pov_character', 'third person limited')}

SETTING DETAILS:
{setting_text}

CHARACTER REACTIONS:
{reactions_text or "No character reactions provided."}

DIALOGUE TO INCORPORATE:
{dialogue_text or "Generate appropriate dialogue."}

WRITING INSTRUCTIONS:
- Write in third person limited POV from {scene_plan.get('pov_character', 'the protagonist')}'s perspective
- Show, don't tell — use sensory details and body language
- Weave dialogue naturally into the narrative
- Follow the beat structure but make transitions smooth
- Create vivid, immersive prose
- Vary sentence length and structure for rhythm
- End the scene with forward momentum

Write the complete scene as polished prose. No meta-commentary or notes — only the story text."""
        return await self.generate(prompt, max_tokens=self.config.max_context_tokens)

    async def revise(self, text: str, feedback: list[str]) -> str:
        """Revise text based on feedback."""
        feedback_text = "\n".join(f"- {f}" for f in feedback)
        prompt = f"""Revise this chapter draft based on the following feedback.

FEEDBACK:
{feedback_text}

CURRENT DRAFT:
{text}

INSTRUCTIONS:
- Address each piece of feedback specifically
- Maintain the overall structure and voice
- Preserve what works well
- Make targeted improvements, not wholesale rewrites

Write the revised version. Only output the revised text, no commentary."""
        return await self.generate(prompt, max_tokens=self.config.max_context_tokens)

    async def compose_chapter(
        self,
        scenes: list[str],
        chapter_title: str = "",
        chapter_number: int = 0,
    ) -> str:
        """Stitch scenes together with transitions into a full chapter."""
        scenes_text = "\n\n---SCENE BREAK---\n\n".join(scenes)
        prompt = f"""Assemble these scenes into a cohesive chapter. Add smooth transitions between scenes where needed.

{"Chapter " + str(chapter_number) + ": " + chapter_title if chapter_title else ""}

SCENES:
{scenes_text}

INSTRUCTIONS:
- Add brief transitions between scenes if needed
- Ensure consistent tone throughout
- The chapter should read as one continuous piece, not separate fragments
- Add a chapter opening line if the first scene doesn't have one
- Do NOT add a chapter heading — just the prose

Write the complete chapter. Only output the story text."""
        return await self.generate(prompt, max_tokens=self.config.max_context_tokens)

"""WorldAgent — maintains world consistency, lore, and setting."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from storyforge.agents.base import AgentConfig, BaseAgent, strip_json_fences
from storyforge.agents.registry import AgentRegistry
from storyforge.events.types import Event, EventType

logger = logging.getLogger(__name__)


@AgentRegistry.register("world")
class WorldAgent(BaseAgent):
    """Maintains world consistency — lore, rules, setting, geography."""

    async def handle_event(self, event: Event) -> Optional[Event]:
        handlers = {
            EventType.WORLD_QUERY: self._handle_query,
            EventType.SETTING_VALIDATION_REQUEST: self._handle_validation,
            EventType.LORE_CHECK: self._handle_lore_check,
            EventType.CONSISTENCY_CHECK_REQUEST: self._handle_consistency_check,
        }
        handler = handlers.get(event.event_type)
        if handler:
            return await handler(event)
        return None

    async def _handle_query(self, event: Event) -> Event:
        query = event.payload.get("query", "")
        context = event.payload.get("context", "")
        answer = await self.answer_query(query, context)
        return event.create_response(
            EventType.WORLD_RESPONSE,
            {"answer": answer},
            self.config.name,
        )

    async def _handle_validation(self, event: Event) -> Event:
        scene_plan = event.payload.get("scene_plan", {})
        enriched = await self.validate_and_enrich_setting(scene_plan)
        return event.create_response(
            EventType.SETTING_VALIDATION_RESULT,
            {"enriched_setting": enriched},
            self.config.name,
        )

    async def _handle_lore_check(self, event: Event) -> Event:
        content = event.payload.get("content", "")
        result = await self.check_lore(content)
        return event.create_response(
            EventType.LORE_RESPONSE,
            {"result": result},
            self.config.name,
        )

    async def _handle_consistency_check(self, event: Event) -> Event:
        chapter_text = event.payload.get("chapter_text", "")
        issues = await self.check_consistency(chapter_text)
        return event.create_response(
            EventType.CONSISTENCY_CHECK_RESULT,
            {"issues": issues},
            self.config.name,
        )

    async def answer_query(self, query: str, context: str = "") -> str:
        """Answer a specific question about the world."""
        world_context = await self._build_world_context()
        prompt = f"""Based on the world bible below, answer this question.

World Bible:
{world_context}

{"Additional context: " + context if context else ""}

Question: {query}

Answer accurately and consistently with established world rules. If the answer is not established, create a plausible answer that is consistent with the world."""
        return await self.generate(prompt)

    async def validate_and_enrich_setting(
        self, scene_plan: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate a scene's setting and enrich with world-consistent details."""
        world_context = await self._build_world_context()
        prompt = f"""Review this scene plan against the world bible and enrich it with setting details.

World Bible:
{world_context}

Scene Plan:
- Location: {scene_plan.get('location', 'unknown')}
- Characters present: {scene_plan.get('characters_present', [])}
- Scene goal: {scene_plan.get('scene_goal', '')}

Provide a JSON response with:
1. "valid": true/false - whether the scene is consistent with world rules
2. "corrections": list of any inconsistencies found
3. "setting_details": sensory details (sights, sounds, smells, atmosphere)
4. "relevant_lore": any world lore relevant to this scene
5. "environment": weather, time of day, ambient conditions

Respond ONLY with valid JSON."""
        response = await self.generate(prompt, temperature=0.4)
        try:
            return json.loads(strip_json_fences(response))
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse setting validation JSON: %s. Response: %.200s",
                e, response,
            )
            return {
                "valid": True,
                "corrections": [],
                "setting_details": response,
                "relevant_lore": "",
                "environment": "",
            }

    async def check_lore(self, content: str) -> dict[str, Any]:
        """Check content against established lore."""
        world_context = await self._build_world_context()
        prompt = f"""Check the following content for consistency with the world bible.

World Bible:
{world_context}

Content to check:
{content}

List any lore violations or inconsistencies. If everything is consistent, say "No issues found."
Respond as JSON: {{"consistent": true/false, "issues": [...]}}"""
        response = await self.generate(prompt, temperature=0.3)
        try:
            return json.loads(strip_json_fences(response))
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse lore check JSON: %s. Response: %.200s",
                e, response,
            )
            return {"consistent": True, "issues": []}

    async def check_consistency(self, chapter_text: str) -> list[str]:
        """Check a chapter draft for world consistency issues."""
        world_context = await self._build_world_context()
        prompt = f"""Review this chapter draft for consistency with the world bible.

World Bible:
{world_context}

Chapter Draft:
{chapter_text[:3000]}

List ONLY genuine inconsistencies with world rules, geography, magic systems, or established facts. Be specific about what's wrong and what the correct information should be.

Respond as JSON array of strings. If no issues, respond with [].
"""
        response = await self.generate(prompt, temperature=0.3)
        try:
            result = json.loads(strip_json_fences(response))
            return result if isinstance(result, list) else []
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse consistency check JSON: %s. Response: %.200s",
                e, response,
            )
            return []

    async def _build_world_context(self) -> str:
        """Build world context from memory."""
        world_data = self.memory.to_text(max_length=6000) if hasattr(self.memory, 'to_text') else ""
        if not world_data:
            # Try to get structured sections
            sections = []
            for key in ["setting", "geography", "magic", "history", "factions", "rules"]:
                value = await self.memory.retrieve(key)
                if value:
                    sections.append(f"## {key.title()}\n{value}")
            world_data = "\n\n".join(sections)
        return world_data or "No world data available."

"""ExpansionAgent — expands extracted scene data into rich visual narratives."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from storyforge.agents.base import BaseAgent, strip_json_fences
from storyforge.agents.registry import AgentRegistry
from storyforge.events.types import Event, EventType

logger = logging.getLogger(__name__)


@AgentRegistry.register("expansion")
class ExpansionAgent(BaseAgent):
    """Expands extracted scene info into rich, detailed visual narratives."""

    async def handle_event(self, event: Event) -> Optional[Event]:
        if event.event_type == EventType.VISUAL_EXPAND_REQUEST:
            return await self._handle_expand(event)
        return None

    async def _handle_expand(self, event: Event) -> Event:
        extraction = event.payload.get("extraction", {})
        expanded = await self.expand(extraction)
        return event.create_response(
            EventType.VISUAL_EXPAND_RESULT,
            {"expanded_scenes": expanded},
            self.config.name,
        )

    async def expand(self, extraction: dict[str, Any]) -> list[dict[str, Any]]:
        """Expand extracted data into detailed visual scene descriptions."""
        scenes = extraction.get("scenes", [])
        characters = extraction.get("characters", [])
        visual_style = extraction.get("visual_style", {})
        mood = extraction.get("mood", "")
        setting = extraction.get("setting", "")

        expanded_scenes = []
        for scene in scenes:
            expanded = await self._expand_single_scene(
                scene, characters, visual_style, mood, setting
            )
            expanded_scenes.append(expanded)

        # If no scenes were extracted, create one from the raw description
        if not expanded_scenes and extraction.get("raw_description"):
            expanded = await self._expand_from_raw(
                extraction["raw_description"], visual_style, mood
            )
            expanded_scenes.append(expanded)

        return expanded_scenes

    async def _expand_single_scene(
        self,
        scene: dict[str, Any],
        characters: list[dict[str, Any]],
        visual_style: dict[str, Any],
        mood: str,
        setting: str,
    ) -> dict[str, Any]:
        prompt = f"""Expand this scene into a rich, detailed visual narrative.

SCENE:
{json.dumps(scene, indent=2, ensure_ascii=False)}

CHARACTERS IN SCENE:
{json.dumps(characters, indent=2, ensure_ascii=False)}

VISUAL STYLE:
{json.dumps(visual_style, indent=2, ensure_ascii=False)}

MOOD: {mood}
SETTING: {setting}

Include:
1. Detailed environment (architecture, landscape, weather, time cues)
2. Character appearances, positions, expressions, clothing
3. Lighting: direction, color temperature, shadows, highlights
4. Color palette: dominant and accent colors
5. Atmosphere: particles, fog, rain, dust, energy effects
6. Camera: suggested angle, depth of field, focal point
7. Motion: what is moving, how, implied dynamics

Respond as JSON:
{{
    "scene_narrative": "rich prose description (3-5 paragraphs)",
    "image_prompt": "optimized prompt for image generation (1-2 paragraphs)",
    "video_prompt": "optimized prompt for video generation (includes motion and temporal direction)",
    "lighting": "lighting description",
    "color_palette": ["color1", "color2"],
    "camera_direction": "camera angle and movement",
    "mood_keywords": ["keyword1", "keyword2"]
}}"""
        response = await self.generate(prompt, temperature=0.7)
        try:
            return json.loads(strip_json_fences(response))
        except json.JSONDecodeError:
            logger.warning("Failed to parse expansion JSON")
            return {
                "scene_narrative": response,
                "image_prompt": scene.get("description", ""),
                "video_prompt": scene.get("description", ""),
            }

    async def _expand_from_raw(
        self,
        raw_description: str,
        visual_style: dict[str, Any],
        mood: str,
    ) -> dict[str, Any]:
        prompt = f"""Expand this description into a rich visual narrative.

RAW DESCRIPTION:
{raw_description}

VISUAL STYLE: {json.dumps(visual_style, ensure_ascii=False)}
MOOD: {mood}

Create detailed scene_narrative, image_prompt, and video_prompt.
Respond as JSON with scene_narrative, image_prompt, video_prompt, lighting, color_palette, camera_direction, mood_keywords."""
        response = await self.generate(prompt, temperature=0.7)
        try:
            return json.loads(strip_json_fences(response))
        except json.JSONDecodeError:
            return {
                "scene_narrative": response,
                "image_prompt": raw_description,
                "video_prompt": raw_description,
            }

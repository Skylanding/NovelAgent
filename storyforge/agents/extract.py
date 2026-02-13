"""ExtractAgent — analyzes input text/images to extract visual scene data."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, Optional

from storyforge.agents.base import BaseAgent, strip_json_fences
from storyforge.agents.registry import AgentRegistry
from storyforge.events.types import Event, EventType

logger = logging.getLogger(__name__)


@AgentRegistry.register("extract")
class ExtractAgent(BaseAgent):
    """Analyzes input text/images using GPT-4o vision to extract scene data."""

    async def handle_event(self, event: Event) -> Optional[Event]:
        if event.event_type == EventType.VISUAL_EXTRACT_REQUEST:
            return await self._handle_extract(event)
        return None

    async def _handle_extract(self, event: Event) -> Event:
        text_input = event.payload.get("text", "")
        image_paths = event.payload.get("image_paths", [])
        image_urls = event.payload.get("image_urls", [])
        extraction = await self.extract(text_input, image_paths, image_urls)
        return event.create_response(
            EventType.VISUAL_EXTRACT_RESULT,
            {"extraction": extraction},
            self.config.name,
        )

    async def extract(
        self,
        text: str = "",
        image_paths: list[str] | None = None,
        image_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        """Extract scene descriptions, characters, styles from text/images."""
        image_paths = image_paths or []
        image_urls = image_urls or []

        extraction_prompt = f"""Analyze the following input and extract structured visual scene information.

INPUT TEXT:
{text if text else "(no text provided)"}

Extract the following in JSON format:
{{
    "scenes": [
        {{
            "description": "detailed visual description of the scene",
            "location": "where this takes place",
            "time_of_day": "morning/afternoon/evening/night",
            "weather": "weather conditions",
            "key_elements": ["important visual elements"],
            "camera_angle": "suggested camera perspective",
            "lighting": "lighting description"
        }}
    ],
    "characters": [
        {{
            "name": "character name if identifiable",
            "appearance": "detailed physical description",
            "clothing": "what they are wearing",
            "expression": "facial expression / emotional display",
            "pose": "body posture and positioning"
        }}
    ],
    "visual_style": {{
        "art_style": "photorealistic/cinematic/painterly/anime/etc",
        "color_palette": "dominant colors and tones",
        "mood": "overall visual mood",
        "references": "any visual style references detected"
    }},
    "mood": "overall emotional mood",
    "setting": "overall setting description",
    "raw_description": "a unified prose description of everything observed"
}}"""

        # Build multimodal content blocks for GPT-4o vision
        content_blocks: list[dict[str, Any]] = [
            {"type": "text", "text": extraction_prompt}
        ]

        for img_path in image_paths:
            path = Path(img_path)
            if path.exists():
                b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
                suffix = path.suffix.lower().lstrip(".")
                mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                        "gif": "gif", "webp": "webp"}.get(suffix, "jpeg")
                content_blocks.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{mime};base64,{b64}"},
                })

        for img_url in image_urls:
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": img_url},
            })

        # Use LLM directly for multimodal content blocks
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": content_blocks},
        ]

        response = await self.llm.generate(
            messages=messages,
            temperature=0.4,
            max_tokens=4096,
        )

        try:
            return json.loads(strip_json_fences(response.content))
        except json.JSONDecodeError:
            logger.warning("Failed to parse extraction JSON, returning raw")
            return {
                "scenes": [],
                "characters": [],
                "visual_style": {},
                "mood": "unknown",
                "setting": text[:200] if text else "unknown",
                "raw_description": response.content,
            }

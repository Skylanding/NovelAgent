"""VisualAgent — generates images and videos from expanded narratives."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from storyforge.agents.base import AgentConfig, BaseAgent
from storyforge.agents.registry import AgentRegistry
from storyforge.events.bus import EventBus
from storyforge.events.types import Event, EventType
from storyforge.llm.base import LLMBackend
from storyforge.memory.base import MemoryStore
from storyforge.visual.base import GenerationStatus, VisualBackend

logger = logging.getLogger(__name__)


@AgentRegistry.register("visual")
class VisualAgent(BaseAgent):
    """Generates optimized prompts and calls visual backends."""

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMBackend,
        memory: MemoryStore,
        event_bus: EventBus,
        image_backend: Optional[VisualBackend] = None,
        video_backend: Optional[VisualBackend] = None,
        prompt_dir: Optional[Path] = None,
    ) -> None:
        super().__init__(config, llm, memory, event_bus, prompt_dir)
        self._image_backend = image_backend
        self._video_backend = video_backend

    async def handle_event(self, event: Event) -> Optional[Event]:
        if event.event_type == EventType.VISUAL_GENERATE_REQUEST:
            return await self._handle_generate(event)
        return None

    async def _handle_generate(self, event: Event) -> Event:
        expanded_scene = event.payload.get("expanded_scene", {})
        output_dir = event.payload.get("output_dir", "output/visuals")
        scene_index = event.payload.get("scene_index", 0)
        generate_image = event.payload.get("generate_image", True)
        generate_video = event.payload.get("generate_video", True)
        image_size = event.payload.get("image_size")
        video_size = event.payload.get("video_size")
        video_duration = event.payload.get("video_duration", 8)

        results = await self.generate_visuals(
            expanded_scene=expanded_scene,
            output_dir=output_dir,
            scene_index=scene_index,
            generate_image=generate_image,
            generate_video=generate_video,
            image_size=image_size,
            video_size=video_size,
            video_duration=video_duration,
        )

        return event.create_response(
            EventType.VISUAL_GENERATE_RESULT,
            {"visual_results": results},
            self.config.name,
        )

    async def generate_visuals(
        self,
        expanded_scene: dict[str, Any],
        output_dir: str,
        scene_index: int = 0,
        generate_image: bool = True,
        generate_video: bool = True,
        image_size: Optional[str] = None,
        video_size: Optional[str] = None,
        video_duration: int = 8,
    ) -> dict[str, Any]:
        """Generate image and/or video for a scene."""
        results: dict[str, Any] = {"scene_index": scene_index}

        # Optimize prompts using LLM
        image_prompt = expanded_scene.get("image_prompt", "")
        video_prompt = expanded_scene.get("video_prompt", "")

        if image_prompt:
            image_prompt = await self._optimize_prompt(image_prompt, "image")
        if video_prompt:
            video_prompt = await self._optimize_prompt(video_prompt, "video")

        tasks = []
        if generate_image and self._image_backend and image_prompt:
            tasks.append(
                self._generate_image(image_prompt, output_dir, scene_index, image_size)
            )
        if generate_video and self._video_backend and video_prompt:
            tasks.append(
                self._generate_video(
                    video_prompt, output_dir, scene_index, video_size, video_duration
                )
            )

        if tasks:
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for item in gathered:
                if isinstance(item, dict):
                    results.update(item)
                elif isinstance(item, Exception):
                    logger.error("Visual generation failed: %s", item)
                    results.setdefault("errors", []).append(str(item))

        return results

    async def _optimize_prompt(self, raw_prompt: str, media_type: str) -> str:
        """Use the LLM to optimize a visual generation prompt."""
        if media_type == "video":
            instruction = (
                "Optimize this prompt for Sora 2 video generation. "
                "Include motion descriptions, temporal flow, camera movement. "
                "Keep under 500 characters. Be vivid and specific."
            )
        else:
            instruction = (
                "Optimize this prompt for DALL-E 3 image generation. "
                "Focus on composition, lighting, style, and detail. "
                "Keep under 400 characters. Be vivid and specific."
            )

        optimize_prompt = f"""{instruction}

Original prompt:
{raw_prompt}

Write ONLY the optimized prompt, nothing else."""
        return await self.generate(optimize_prompt, temperature=0.5)

    async def _generate_image(
        self,
        prompt: str,
        output_dir: str,
        scene_index: int,
        size: Optional[str],
    ) -> dict[str, Any]:
        result = await self._image_backend.generate(prompt=prompt, size=size)
        if result.status == GenerationStatus.COMPLETED and result.url:
            file_path = str(Path(output_dir) / f"scene_{scene_index:03d}.png")
            await self._image_backend.download(result, file_path)
            return {
                "image": {
                    "path": file_path,
                    "prompt_used": prompt,
                    "revised_prompt": result.revised_prompt,
                }
            }
        return {"image": {"error": "Generation did not complete"}}

    async def _generate_video(
        self,
        prompt: str,
        output_dir: str,
        scene_index: int,
        size: Optional[str],
        duration: int,
    ) -> dict[str, Any]:
        result = await self._video_backend.generate(
            prompt=prompt, size=size, duration=duration
        )
        # Poll for completion if the job is still pending
        if result.status in (GenerationStatus.PENDING, GenerationStatus.PROCESSING):
            if hasattr(self._video_backend, "wait_for_completion") and result.job_id:
                result = await self._video_backend.wait_for_completion(
                    result.job_id, poll_interval=10.0, timeout=600.0
                )

        if result.status == GenerationStatus.COMPLETED:
            file_path = str(Path(output_dir) / f"scene_{scene_index:03d}.mp4")
            await self._video_backend.download(result, file_path)
            return {
                "video": {
                    "path": file_path,
                    "prompt_used": prompt,
                    "duration": result.duration_seconds,
                }
            }
        return {"video": {"error": result.error or "Generation failed"}}

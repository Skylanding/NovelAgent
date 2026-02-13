"""Visual pipeline — orchestrates Extract → Expand → Generate stages."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from storyforge.agents.expansion import ExpansionAgent
from storyforge.agents.extract import ExtractAgent
from storyforge.agents.visual_agent import VisualAgent
from storyforge.visual.output import VisualOutputManager

logger = logging.getLogger(__name__)


class VisualPipeline:
    """Orchestrates the visual generation pipeline.

    Stages:
      1. Extract  — analyse input text/images into structured scene data
      2. Expand   — enrich each scene into detailed visual narratives
      3. Generate — produce images (DALL-E 3) and videos (Sora 2) per scene
    """

    def __init__(
        self,
        extract_agent: ExtractAgent,
        expansion_agent: ExpansionAgent,
        visual_agent: VisualAgent,
        output_manager: VisualOutputManager,
        generate_images: bool = True,
        generate_videos: bool = True,
        video_duration: int = 8,
        parallel_scenes: bool = True,
        image_size: Optional[str] = None,
        video_size: Optional[str] = None,
    ) -> None:
        self._extract = extract_agent
        self._expand = expansion_agent
        self._visual = visual_agent
        self._output = output_manager
        self._gen_images = generate_images
        self._gen_videos = generate_videos
        self._video_duration = video_duration
        self._parallel = parallel_scenes
        self._image_size = image_size
        self._video_size = video_size

    async def run(
        self,
        text: str = "",
        image_paths: list[str] | None = None,
        image_urls: list[str] | None = None,
        image_size: Optional[str] = None,
        video_size: Optional[str] = None,
        video_duration: Optional[int] = None,
    ) -> dict[str, Any]:
        """Execute the full visual pipeline and return a manifest dict."""
        image_paths = image_paths or []
        image_urls = image_urls or []
        image_size = image_size or self._image_size
        video_size = video_size or self._video_size
        video_duration = video_duration or self._video_duration

        await self._output.initialize()

        # ── Stage 1: Extract ──────────────────────────────────────────
        logger.info("[Visual Stage 1] Extracting scene data...")
        extraction = await self._extract.extract(
            text=text,
            image_paths=image_paths,
            image_urls=image_urls,
        )
        await self._output.save_intermediate("extraction", extraction)
        logger.info(
            "  Extracted %d scene(s), %d character(s)",
            len(extraction.get("scenes", [])),
            len(extraction.get("characters", [])),
        )

        # ── Stage 2: Expand ───────────────────────────────────────────
        logger.info("[Visual Stage 2] Expanding into visual narratives...")
        expanded_scenes = await self._expand.expand(extraction)
        await self._output.save_intermediate("expanded_scenes", expanded_scenes)
        logger.info("  Expanded %d scene(s)", len(expanded_scenes))

        # ── Stage 3: Generate visuals ─────────────────────────────────
        logger.info("[Visual Stage 3] Generating visuals...")
        output_dir = str(self._output.visuals_dir)

        if self._parallel:
            tasks = [
                self._visual.generate_visuals(
                    expanded_scene=scene,
                    output_dir=output_dir,
                    scene_index=idx,
                    generate_image=self._gen_images,
                    generate_video=self._gen_videos,
                    image_size=image_size,
                    video_size=video_size,
                    video_duration=video_duration,
                )
                for idx, scene in enumerate(expanded_scenes)
            ]
            visual_results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            visual_results = []
            for idx, scene in enumerate(expanded_scenes):
                try:
                    result = await self._visual.generate_visuals(
                        expanded_scene=scene,
                        output_dir=output_dir,
                        scene_index=idx,
                        generate_image=self._gen_images,
                        generate_video=self._gen_videos,
                        image_size=image_size,
                        video_size=video_size,
                        video_duration=video_duration,
                    )
                    visual_results.append(result)
                except Exception as exc:
                    logger.error("Scene %d generation failed: %s", idx, exc)
                    visual_results.append({"scene_index": idx, "error": str(exc)})

        # Clean up gathered exceptions
        cleaned_results = []
        for r in visual_results:
            if isinstance(r, Exception):
                logger.error("Scene generation exception: %s", r)
                cleaned_results.append({"error": str(r)})
            else:
                cleaned_results.append(r)

        # ── Build manifest ────────────────────────────────────────────
        manifest: dict[str, Any] = {
            "input": {
                "text": text[:500] if text else "",
                "image_paths": image_paths,
                "image_urls": image_urls,
            },
            "extraction_summary": {
                "scene_count": len(extraction.get("scenes", [])),
                "character_count": len(extraction.get("characters", [])),
                "mood": extraction.get("mood", ""),
            },
            "expanded_scene_count": len(expanded_scenes),
            "visual_results": cleaned_results,
            "settings": {
                "generate_images": self._gen_images,
                "generate_videos": self._gen_videos,
                "video_duration": video_duration,
                "image_size": image_size,
                "video_size": video_size,
            },
        }

        manifest_path = await self._output.save_manifest(manifest)
        logger.info("Visual pipeline complete. Manifest: %s", manifest_path)

        return manifest

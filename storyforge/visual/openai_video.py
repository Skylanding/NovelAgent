"""Sora 2 video generation backend."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

import httpx
from openai import AsyncOpenAI

from storyforge.visual.base import (
    GenerationStatus,
    MediaType,
    VisualBackend,
    VisualConfig,
    VisualResult,
)

logger = logging.getLogger(__name__)

# Map Sora API status strings to our enum
_STATUS_MAP = {
    "pending": GenerationStatus.PENDING,
    "in_progress": GenerationStatus.PROCESSING,
    "running": GenerationStatus.PROCESSING,
    "completed": GenerationStatus.COMPLETED,
    "failed": GenerationStatus.FAILED,
}


class Sora2Backend(VisualBackend):
    """Generates videos using OpenAI Sora 2.

    Uses the official OpenAI Python SDK ``client.videos`` interface:
      - ``client.videos.create()``  — submit a generation job
      - ``client.videos.retrieve()`` — poll job status
      - ``client.videos.create_and_poll()`` — convenience wrapper
    """

    def __init__(self, config: VisualConfig) -> None:
        super().__init__(config)
        kwargs: dict[str, Any] = {}
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self._client = AsyncOpenAI(**kwargs)

    @property
    def media_type(self) -> MediaType:
        return MediaType.VIDEO

    async def generate(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        **kwargs: Any,
    ) -> VisualResult:
        """Submit a video generation job to Sora 2.

        Returns a result with PENDING/COMPLETED status depending on whether
        ``create_and_poll`` is used (controlled by ``wait`` kwarg).
        """
        size = size or self.config.default_size
        duration = kwargs.get("duration", 8)
        wait = kwargs.get("wait", False)

        # Build common create kwargs
        create_kwargs: dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
        }
        # Only pass supported optional params if provided
        if size:
            create_kwargs["size"] = size
        if duration:
            create_kwargs["duration"] = duration

        try:
            if wait:
                # Blocking convenience: polls internally until done
                video = await self._client.videos.create_and_poll(**create_kwargs)
            else:
                video = await self._client.videos.create(**create_kwargs)

            status_str = getattr(video, "status", "pending")
            video_url = getattr(video, "url", None) or getattr(
                video, "video_url", None
            )
            video_duration = getattr(video, "duration", None)

            return VisualResult(
                media_type=MediaType.VIDEO,
                status=_STATUS_MAP.get(status_str, GenerationStatus.PENDING),
                job_id=getattr(video, "id", ""),
                url=video_url,
                duration_seconds=video_duration,
                model=self.config.model,
                raw_response=video,
            )
        except Exception as exc:
            logger.error("Sora 2 generation failed: %s", exc)
            return VisualResult(
                media_type=MediaType.VIDEO,
                status=GenerationStatus.FAILED,
                model=self.config.model,
                error=str(exc),
            )

    async def poll_status(self, job_id: str) -> VisualResult:
        """Check the status of a video generation job."""
        try:
            video = await self._client.videos.retrieve(job_id)

            status_str = getattr(video, "status", "pending")
            video_url = getattr(video, "url", None) or getattr(
                video, "video_url", None
            )
            duration = getattr(video, "duration", None)
            error = getattr(video, "error", None)

            return VisualResult(
                media_type=MediaType.VIDEO,
                status=_STATUS_MAP.get(status_str, GenerationStatus.PENDING),
                job_id=job_id,
                url=video_url,
                duration_seconds=duration,
                model=self.config.model,
                raw_response=video,
                error=str(error) if error else None,
            )
        except Exception as exc:
            logger.error("Sora 2 poll failed for job %s: %s", job_id, exc)
            return VisualResult(
                media_type=MediaType.VIDEO,
                status=GenerationStatus.FAILED,
                job_id=job_id,
                model=self.config.model,
                error=str(exc),
            )

    async def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 10.0,
        timeout: float = 600.0,
    ) -> VisualResult:
        """Poll until the video job completes or times out."""
        elapsed = 0.0
        while elapsed < timeout:
            result = await self.poll_status(job_id)
            if result.status == GenerationStatus.COMPLETED:
                return result
            if result.status == GenerationStatus.FAILED:
                return result
            logger.info(
                "Sora 2 job %s status: %s (%.0fs elapsed)",
                job_id,
                result.status.value,
                elapsed,
            )
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        return VisualResult(
            media_type=MediaType.VIDEO,
            status=GenerationStatus.FAILED,
            job_id=job_id,
            model=self.config.model,
            error=f"Timed out after {timeout}s",
        )

    async def download(self, result: VisualResult, output_path: str) -> str:
        """Download the generated video to a local file."""
        if not result.url:
            raise ValueError("No URL in result to download")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(result.url)
            resp.raise_for_status()
            output.write_bytes(resp.content)

        logger.info("Downloaded video to %s", output_path)
        result.local_path = output_path
        return output_path

    async def health_check(self) -> bool:
        try:
            await self._client.models.retrieve(self.config.model)
            return True
        except Exception:
            logger.exception("Sora 2 health check failed")
            return False

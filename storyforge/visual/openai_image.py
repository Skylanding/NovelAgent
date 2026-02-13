"""DALL-E 3 image generation backend."""

from __future__ import annotations

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


class DallE3Backend(VisualBackend):
    """Generates images using OpenAI DALL-E 3."""

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
        return MediaType.IMAGE

    async def generate(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        **kwargs: Any,
    ) -> VisualResult:
        """Generate an image synchronously via DALL-E 3."""
        size = size or self.config.default_size
        quality = quality or self.config.default_quality
        style = style or self.config.default_style

        try:
            response = await self._client.images.generate(
                model=self.config.model,
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=1,
                response_format="url",
            )

            image_data = response.data[0]
            return VisualResult(
                media_type=MediaType.IMAGE,
                status=GenerationStatus.COMPLETED,
                url=image_data.url,
                revised_prompt=image_data.revised_prompt,
                model=self.config.model,
                raw_response=response,
            )
        except Exception as exc:
            logger.error("DALL-E 3 generation failed: %s", exc)
            return VisualResult(
                media_type=MediaType.IMAGE,
                status=GenerationStatus.FAILED,
                model=self.config.model,
                error=str(exc),
            )

    async def poll_status(self, job_id: str) -> VisualResult:
        """DALL-E 3 is synchronous — no polling needed."""
        return VisualResult(
            media_type=MediaType.IMAGE,
            status=GenerationStatus.COMPLETED,
            model=self.config.model,
        )

    async def download(self, result: VisualResult, output_path: str) -> str:
        """Download the generated image to a local file."""
        if not result.url:
            raise ValueError("No URL in result to download")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(result.url)
            resp.raise_for_status()
            output.write_bytes(resp.content)

        logger.info("Downloaded image to %s", output_path)
        result.local_path = output_path
        return output_path

    async def health_check(self) -> bool:
        try:
            await self._client.models.retrieve(self.config.model)
            return True
        except Exception:
            logger.exception("DALL-E 3 health check failed")
            return False

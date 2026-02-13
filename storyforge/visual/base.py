"""Abstract visual backend interface for image and video generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class VisualConfig:
    """Configuration for a visual backend instance."""

    provider: str  # "openai_image", "openai_video"
    model: str  # "dall-e-3", "sora-2"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    requests_per_minute: int = 10
    default_size: str = "1024x1024"
    default_quality: str = "standard"
    default_style: str = "natural"


@dataclass
class VisualResult:
    """Result of a visual generation request."""

    media_type: MediaType
    status: GenerationStatus
    job_id: Optional[str] = None
    url: Optional[str] = None
    local_path: Optional[str] = None
    revised_prompt: Optional[str] = None
    duration_seconds: Optional[float] = None
    model: str = ""
    raw_response: Optional[Any] = None
    error: Optional[str] = None


class VisualBackend(ABC):
    """Abstract interface for visual generation providers."""

    def __init__(self, config: VisualConfig) -> None:
        self.config = config

    @property
    @abstractmethod
    def media_type(self) -> MediaType:
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        **kwargs: Any,
    ) -> VisualResult:
        """Submit a generation request. For video, returns a pending job."""
        ...

    @abstractmethod
    async def poll_status(self, job_id: str) -> VisualResult:
        """Check status of an async generation job."""
        ...

    @abstractmethod
    async def download(self, result: VisualResult, output_path: str) -> str:
        """Download generated media to a local file. Returns file path."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the backend is reachable."""
        ...

"""Abstract LLM backend interface and shared types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional


class ModelTier(str, Enum):
    """Model size tiers for agent assignment."""

    SMALL = "small"  # 7B-13B local models
    MEDIUM = "medium"  # 30B-70B or mid-tier API
    LARGE = "large"  # Frontier models (Claude Opus, GPT-4)


@dataclass
class LLMResponse:
    """Standardized response from any LLM backend."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str
    raw_response: Optional[Any] = None


@dataclass
class LLMConfig:
    """Configuration for an LLM backend instance."""

    provider: str
    model: str
    tier: ModelTier = ModelTier.SMALL
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    max_tokens: int = 4096
    default_temperature: float = 0.7
    requests_per_minute: int = 60
    context_window: int = 8192


class LLMBackend(ABC):
    """Abstract interface for all LLM providers."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[list[str]] = None,
    ) -> LLMResponse:
        """Send messages and receive a complete response."""
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens as they arrive."""
        ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Count tokens for the specific model's tokenizer."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the backend is reachable and the model is available."""
        ...

    @property
    def context_window(self) -> int:
        return self.config.context_window

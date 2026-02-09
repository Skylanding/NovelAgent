"""Abstract memory store interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class MemoryStore(ABC):
    """Abstract interface for agent memory."""

    @abstractmethod
    async def store(
        self, key: str, value: Any, metadata: Optional[dict] = None
    ) -> None:
        """Store a piece of information."""
        ...

    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve by exact key."""
        ...

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Semantic or keyword search for relevant memories."""
        ...

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys, optionally filtered by prefix."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a specific key."""
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear all stored data."""
        ...

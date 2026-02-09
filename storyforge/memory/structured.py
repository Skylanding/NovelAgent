"""JSON-backed structured memory for organized data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from storyforge.memory.base import MemoryStore


class StructuredMemory(MemoryStore):
    """JSON-backed structured memory for world bibles, plot outlines, etc."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self._storage_path = storage_path
        self._data: dict[str, Any] = {}

    async def store(
        self, key: str, value: Any, metadata: Optional[dict] = None
    ) -> None:
        """Store with dotted key support: 'world.magic.rules'."""
        parts = key.split(".")
        target = self._data
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve by dotted key path."""
        parts = key.split(".")
        current = self._data
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Simple keyword search across all stored values."""
        query_lower = query.lower()
        results: list[dict] = []

        def _search_recursive(data: Any, path: str) -> None:
            if isinstance(data, dict):
                for k, v in data.items():
                    _search_recursive(v, f"{path}.{k}" if path else k)
            elif isinstance(data, str) and query_lower in data.lower():
                results.append({"key": path, "content": data})
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    _search_recursive(item, f"{path}[{i}]")

        _search_recursive(self._data, "")
        return results[:top_k]

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all leaf keys, optionally filtered by prefix."""
        keys: list[str] = []

        def _collect(data: Any, path: str) -> None:
            if isinstance(data, dict):
                for k, v in data.items():
                    _collect(v, f"{path}.{k}" if path else k)
            else:
                keys.append(path)

        _collect(self._data, "")
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        return keys

    async def delete(self, key: str) -> None:
        parts = key.split(".")
        current = self._data
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                return
            current = current[part]
        if isinstance(current, dict):
            current.pop(parts[-1], None)

    async def clear(self) -> None:
        self._data.clear()

    async def get_section(self, section: str) -> dict:
        """Get an entire section of structured data."""
        result = await self.retrieve(section)
        if isinstance(result, dict):
            return result
        return {}

    async def load_from_dict(self, data: dict[str, Any]) -> None:
        """Load data from a dictionary (e.g., parsed YAML)."""
        self._data = data

    async def save_to_disk(self) -> None:
        """Persist to JSON file."""
        if self._storage_path:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "w") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)

    async def load_from_disk(self) -> None:
        """Load from JSON file."""
        if self._storage_path and self._storage_path.exists():
            with open(self._storage_path) as f:
                self._data = json.load(f)

    def to_text(self, max_length: int = 0) -> str:
        """Serialize entire memory to a readable text representation."""
        text = json.dumps(self._data, indent=2, ensure_ascii=False)
        if max_length and len(text) > max_length:
            text = text[:max_length] + "\n... (truncated)"
        return text

"""ChromaDB-backed vector memory for semantic search."""

from __future__ import annotations

import logging
from typing import Any, Optional

from storyforge.memory.base import MemoryStore

logger = logging.getLogger(__name__)


class VectorMemory(MemoryStore):
    """ChromaDB-backed vector memory for semantic retrieval."""

    def __init__(
        self,
        collection_name: str,
        persist_directory: str,
    ) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
        )

    async def store(
        self, key: str, value: Any, metadata: Optional[dict] = None
    ) -> None:
        self._collection.upsert(
            documents=[str(value)],
            ids=[key],
            metadatas=[metadata or {}],
        )

    async def retrieve(self, key: str) -> Optional[Any]:
        try:
            result = self._collection.get(ids=[key])
            if result["documents"]:
                return result["documents"][0]
        except Exception as e:
            logger.warning("VectorMemory retrieve failed for key=%s: %s", key, e)
        return None

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
        )
        if not results["ids"] or not results["ids"][0]:
            return []

        return [
            {
                "id": id_,
                "content": doc,
                "metadata": meta,
                "distance": dist,
            }
            for id_, doc, meta, dist in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    async def list_keys(self, prefix: str = "") -> list[str]:
        all_items = self._collection.get()
        keys = all_items["ids"]
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        return keys

    async def delete(self, key: str) -> None:
        try:
            self._collection.delete(ids=[key])
        except Exception as e:
            logger.warning("VectorMemory delete failed for key=%s: %s", key, e)

    async def clear(self) -> None:
        # ChromaDB doesn't have a clear method; delete and recreate
        name = self._collection.name
        self._client.delete_collection(name)
        self._collection = self._client.get_or_create_collection(name=name)

    async def store_batch(
        self,
        keys: list[str],
        values: list[str],
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        """Batch store multiple memories."""
        self._collection.upsert(
            documents=values,
            ids=keys,
            metadatas=metadatas or [{} for _ in keys],
        )

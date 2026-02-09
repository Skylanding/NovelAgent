"""Ollama backend for local model inference."""

from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from ollama import AsyncClient

from storyforge.llm.base import LLMBackend, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class OllamaBackend(LLMBackend):
    """Backend for local models via Ollama."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._client = AsyncClient(
            host=config.base_url or "http://localhost:11434"
        )

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[list[str]] = None,
    ) -> LLMResponse:
        options: dict = {
            "temperature": temperature or self.config.default_temperature,
            "num_predict": max_tokens or self.config.max_tokens,
        }
        if stop_sequences:
            options["stop"] = stop_sequences

        response = await self._client.chat(
            model=self.config.model,
            messages=messages,
            options=options,
        )
        return LLMResponse(
            content=response["message"]["content"],
            model=self.config.model,
            input_tokens=response.get("prompt_eval_count", 0),
            output_tokens=response.get("eval_count", 0),
            finish_reason="stop",
            raw_response=response,
        )

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        options: dict = {
            "temperature": temperature or self.config.default_temperature,
            "num_predict": max_tokens or self.config.max_tokens,
        }
        stream = await self._client.chat(
            model=self.config.model,
            messages=messages,
            options=options,
            stream=True,
        )
        async for chunk in stream:
            if chunk.get("message", {}).get("content"):
                yield chunk["message"]["content"]

    async def count_tokens(self, text: str) -> int:
        # Ollama doesn't expose a tokenizer; use rough heuristic
        return len(text) // 4

    async def health_check(self) -> bool:
        try:
            models = await self._client.list()
            available = [m["name"] for m in models.get("models", [])]
            # Check if our model (or a prefix match) is available
            return any(
                self.config.model in name or name.startswith(self.config.model)
                for name in available
            )
        except Exception:
            logger.exception("Ollama health check failed")
            return False

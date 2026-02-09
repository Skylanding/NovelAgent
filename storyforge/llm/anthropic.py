"""Anthropic Claude backend."""

from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from anthropic import AsyncAnthropic

from storyforge.llm.base import LLMBackend, LLMConfig, LLMResponse
from storyforge.llm.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)


class AnthropicBackend(LLMBackend):
    """Backend for Anthropic Claude models."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._client = AsyncAnthropic(api_key=config.api_key)
        self._limiter = TokenBucketRateLimiter(config.requests_per_minute)

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[list[str]] = None,
    ) -> LLMResponse:
        await self._limiter.acquire()

        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs: dict = {
            "model": self.config.model,
            "messages": chat_messages,
            "temperature": temperature or self.config.default_temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if stop_sequences:
            kwargs["stop_sequences"] = stop_sequences

        response = await self._client.messages.create(**kwargs)

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason or "end_turn",
            raw_response=response,
        )

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        await self._limiter.acquire()

        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs: dict = {
            "model": self.config.model,
            "messages": chat_messages,
            "temperature": temperature or self.config.default_temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        if system_msg:
            kwargs["system"] = system_msg

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    async def count_tokens(self, text: str) -> int:
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            return len(text) // 4

    async def health_check(self) -> bool:
        try:
            # Minimal request to verify connectivity
            await self._client.messages.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception:
            logger.exception("Anthropic health check failed")
            return False

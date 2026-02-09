"""OpenAI backend."""

from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from storyforge.llm.base import LLMBackend, LLMConfig, LLMResponse
from storyforge.llm.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)


class OpenAIBackend(LLMBackend):
    """Backend for OpenAI models."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        kwargs: dict = {}
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self._client = AsyncOpenAI(**kwargs)
        self._limiter = TokenBucketRateLimiter(config.requests_per_minute)

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[list[str]] = None,
    ) -> LLMResponse:
        await self._limiter.acquire()

        kwargs: dict = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.default_temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        if stop_sequences:
            kwargs["stop"] = stop_sequences

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=(
                response.usage.completion_tokens if response.usage else 0
            ),
            finish_reason=choice.finish_reason or "stop",
            raw_response=response,
        )

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        await self._limiter.acquire()

        stream = await self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature or self.config.default_temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def count_tokens(self, text: str) -> int:
        try:
            import tiktoken

            enc = tiktoken.encoding_for_model(self.config.model)
            return len(enc.encode(text))
        except Exception:
            return len(text) // 4

    async def health_check(self) -> bool:
        try:
            await self._client.models.retrieve(self.config.model)
            return True
        except Exception:
            logger.exception("OpenAI health check failed")
            return False

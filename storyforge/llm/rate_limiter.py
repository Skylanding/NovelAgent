"""Token bucket rate limiter for API backends."""

from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Async rate limiter using a token bucket algorithm."""

    def __init__(
        self,
        requests_per_minute: int,
        tokens_per_minute: int = 0,
        acquire_timeout: float = 300.0,
    ) -> None:
        self._rpm = requests_per_minute
        self._tpm = tokens_per_minute
        self._request_tokens = float(requests_per_minute)
        self._token_tokens = float(tokens_per_minute) if tokens_per_minute else 0
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._acquire_timeout = acquire_timeout

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now

        # Refill request tokens
        self._request_tokens = min(
            float(self._rpm),
            self._request_tokens + elapsed * (self._rpm / 60.0),
        )

        # Refill token tokens
        if self._tpm:
            self._token_tokens = min(
                float(self._tpm),
                self._token_tokens + elapsed * (self._tpm / 60.0),
            )

    async def acquire(self, token_count: int = 0) -> None:
        """Wait until a request slot is available.

        Raises TimeoutError if the slot is not available within the timeout.
        """
        start = time.monotonic()
        while True:
            elapsed = time.monotonic() - start
            if elapsed > self._acquire_timeout:
                raise TimeoutError(
                    f"Rate limiter timed out after {self._acquire_timeout:.0f}s "
                    f"waiting for capacity (rpm={self._rpm}, tpm={self._tpm})"
                )
            async with self._lock:
                self._refill()
                has_request = self._request_tokens >= 1.0
                has_tokens = (
                    not self._tpm or self._token_tokens >= token_count
                )
                if has_request and has_tokens:
                    self._request_tokens -= 1.0
                    if self._tpm and token_count:
                        self._token_tokens -= token_count
                    return
            await asyncio.sleep(0.1)

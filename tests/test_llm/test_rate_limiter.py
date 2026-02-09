"""Tests for TokenBucketRateLimiter."""

import asyncio
import time

import pytest

from storyforge.llm.rate_limiter import TokenBucketRateLimiter


@pytest.mark.asyncio
async def test_acquire_basic():
    """Acquiring should succeed immediately when bucket is full."""
    limiter = TokenBucketRateLimiter(requests_per_minute=60)
    await limiter.acquire()  # Should not raise


@pytest.mark.asyncio
async def test_acquire_respects_rpm():
    """After exhausting tokens, acquire should block until refill."""
    limiter = TokenBucketRateLimiter(requests_per_minute=1)
    await limiter.acquire()  # Use the one available token

    # Next acquire should take ~60s for rpm=1, but we use a short timeout
    limiter._acquire_timeout = 0.3
    with pytest.raises(TimeoutError):
        await limiter.acquire()


@pytest.mark.asyncio
async def test_acquire_timeout():
    """Acquire should raise TimeoutError when timeout is exceeded."""
    limiter = TokenBucketRateLimiter(
        requests_per_minute=1,
        acquire_timeout=0.5,
    )
    await limiter.acquire()  # Use the one available token

    start = time.monotonic()
    with pytest.raises(TimeoutError, match="Rate limiter timed out"):
        await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.4  # Should have waited close to timeout


@pytest.mark.asyncio
async def test_acquire_with_tpm():
    """Token-per-minute limit should also be checked."""
    limiter = TokenBucketRateLimiter(
        requests_per_minute=100,
        tokens_per_minute=10,
    )
    await limiter.acquire(token_count=10)  # Use all token budget

    limiter._acquire_timeout = 0.3
    with pytest.raises(TimeoutError):
        await limiter.acquire(token_count=10)


@pytest.mark.asyncio
async def test_refill_restores_capacity():
    """After waiting, tokens should refill."""
    limiter = TokenBucketRateLimiter(requests_per_minute=600)
    # Exhaust all tokens
    for _ in range(600):
        await limiter.acquire()

    # Wait a bit for refill
    await asyncio.sleep(0.15)
    # Should be able to acquire again after refill
    await limiter.acquire()


@pytest.mark.asyncio
async def test_zero_token_count():
    """Acquiring with zero token count should work when TPM is set."""
    limiter = TokenBucketRateLimiter(
        requests_per_minute=60,
        tokens_per_minute=1000,
    )
    await limiter.acquire(token_count=0)  # Should succeed

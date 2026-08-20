"""Tests — Redis rate limit (in-memory fallback, so no Redis needed)."""
import pytest
import asyncio

from gateway.infra.rate_limit import _InMemoryBucket, RateLimiter


@pytest.mark.asyncio
async def test_in_memory_bucket_allows_until_limit():
    bucket = _InMemoryBucket()
    key = "user1"
    for i in range(5):
        allowed, remaining = await bucket.is_allowed(key, max_hits=5, window_s=60)
        assert allowed is True
        assert remaining == 5 - (i + 1)
    # 6th should be blocked
    allowed, remaining = await bucket.is_allowed(key, max_hits=5, window_s=60)
    assert allowed is False
    assert remaining == 0

@pytest.mark.asyncio
async def test_in_memory_bucket_resets_after_window():
    bucket = _InMemoryBucket()
    key = "user2"
    # Fill window=1s
    for _ in range(3):
        await bucket.is_allowed(key, max_hits=3, window_s=1)
    allowed, _ = await bucket.is_allowed(key, max_hits=3, window_s=1)
    assert allowed is False
    await asyncio.sleep(1.1)
    allowed, remaining = await bucket.is_allowed(key, max_hits=3, window_s=1)
    assert allowed is True
    assert remaining == 2

@pytest.mark.asyncio
async def test_in_memory_isolated_keys():
    bucket = _InMemoryBucket()
    await bucket.is_allowed("a", max_hits=1, window_s=60)
    allowed, _ = await bucket.is_allowed("b", max_hits=1, window_s=60)
    assert allowed is True  # b not affected
    allowed, _ = await bucket.is_allowed("a", max_hits=1, window_s=60)
    assert allowed is False

@pytest.mark.asyncio
async def test_rate_limiter_fallback_without_redis():
    # Force in-memory path by pointing to unreachable Redis
    rl = RateLimiter(redis_url="redis://127.0.0.1:6399/0", per_minute=2)
    # Bypass connection attempt failure handling — should still work
    allowed, remaining, ttl = await rl.is_allowed("probe-key", max_hits=2, window_s=60)
    assert allowed is True
    allowed, remaining, ttl = await rl.is_allowed("probe-key", max_hits=2, window_s=60)
    assert allowed is True
    allowed, remaining, ttl = await rl.is_allowed("probe-key", max_hits=2, window_s=60)
    assert allowed is False
    assert remaining == 0
    await rl.close()

@pytest.mark.asyncio
async def test_rate_limiter_reset():
    bucket = _InMemoryBucket()
    await bucket.is_allowed("x", max_hits=1, window_s=60)
    allowed, _ = await bucket.is_allowed("x", max_hits=1, window_s=60)
    assert allowed is False
    await bucket.reset("x")
    allowed, _ = await bucket.is_allowed("x", max_hits=1, window_s=60)
    assert allowed is True

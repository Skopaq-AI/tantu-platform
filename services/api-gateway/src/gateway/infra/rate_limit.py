"""Redis sliding-window rate limit with in-memory fallback.

Production: Redis INCR + EXPIRE (fixed window). Tests/dev without Redis: pure in-memory.

Exposes:
  RateLimiter — async, shared via lifespan.
  _InMemoryBucket — for unit tests without Redis.
"""

from __future__ import annotations

import time
import asyncio
import logging
from collections import defaultdict
from typing import Optional

from .config import settings

log = logging.getLogger("gateway.rate_limit")


class _InMemoryBucket:
    """Thread-safe in-memory fixed window — for tests and Redis-down fallback."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def is_allowed(self, key: str, max_hits: int, window_s: int) -> tuple[bool, int]:
        """Return (allowed, remaining). Mutates bucket."""
        async with self._lock:
            now = time.time()
            lst = self._hits[key]
            # prune
            cutoff = now - window_s
            lst[:] = [t for t in lst if t > cutoff]
            if len(lst) >= max_hits:
                remaining = 0
                return False, remaining
            lst.append(now)
            remaining = max_hits - len(lst)
            return True, remaining

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._hits.pop(key, None)


_mem = _InMemoryBucket()


class RateLimiter:
    """Redis-backed rate limiter with memory fallback."""

    def __init__(self, redis_url: Optional[str] = None, per_minute: Optional[int] = None):
        self.redis_url = redis_url or settings.redis_url
        self.per_minute = per_minute or settings.rate_limit_per_minute
        self._redis = None
        self._redis_available: Optional[bool] = None
        self._mem = _InMemoryBucket()

    async def _ensure_redis(self):
        if self._redis_available is not None:
            return
        try:
            import redis.asyncio as redis  # type: ignore[import-not-found]

            self._redis = redis.from_url(
                self.redis_url, decode_responses=True, socket_connect_timeout=1
            )
            await self._redis.ping()
            self._redis_available = True
            log.info("gateway rate_limit: Redis connected at %s", self.redis_url)
        except Exception as e:
            log.warning("gateway rate_limit: Redis unavailable, using in-memory fallback: %s", e)
            self._redis_available = False
            self._redis = None

    async def is_allowed(
        self,
        key: str,
        max_hits: Optional[int] = None,
        window_s: int = 60,
    ) -> tuple[bool, int, int]:
        """Check if key is allowed.

        Returns (allowed, remaining, reset_after_s).
        Respects per_minute default when max_hits is None.
        """
        await self._ensure_redis()
        limit = max_hits if max_hits is not None else self.per_minute
        if self._redis_available and self._redis is not None:
            try:
                return await self._redis_check(key, limit, window_s)
            except Exception as e:
                log.warning("gateway rate_limit Redis error, fallback: %s", e)
                # fall through to memory
        allowed, remaining = await self._mem.is_allowed(key, limit, window_s)
        # approximate reset
        return allowed, remaining, window_s

    async def _redis_check(self, key: str, limit: int, window_s: int) -> tuple[bool, int, int]:
        assert self._redis is not None
        redis_key = f"ratelimit:{key}"
        # Lua-free fixed window
        count = await self._redis.incr(redis_key)
        if count == 1:
            await self._redis.expire(redis_key, window_s)
        ttl = await self._redis.ttl(redis_key)
        if ttl < 0:
            ttl = window_s
        remaining = max(0, limit - int(count))
        allowed = int(count) <= limit
        return allowed, remaining, int(ttl)

    async def reset(self, key: str) -> None:
        await self._ensure_redis()
        if self._redis_available and self._redis is not None:
            try:
                await self._redis.delete(f"ratelimit:{key}")
            except Exception:
                pass
        await self._mem.reset(key)

    async def close(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception:
                pass


# Global singleton for app lifespan
rate_limiter = RateLimiter()

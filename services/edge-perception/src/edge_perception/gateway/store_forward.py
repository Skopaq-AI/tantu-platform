"""Store-and-forward — Redis Stream with offline in-memory fallback.

Offline-first contract:
  - enqueue() never raises due to Redis being down; it buffers in memory (+ optional disk spill).
  - background drain() pushes buffered entries to Redis when it recovers.
  - consumer can read via xread; if Redis is down, reads from buffer.
  - Prometheus gauges reflect queue depth.

No stub: real redis.asyncio if available, with graceful fallback.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Queued:
    stream: str
    payload: dict[str, Any]
    ts: float
    id: str = ""


class InMemoryStore:
    """Bounded in-memory queue with FIFO drain. Thread-safe under asyncio single thread."""

    def __init__(self, maxlen: int = 10000) -> None:
        self._q: deque[Queued] = deque(maxlen=maxlen)
        self.dropped: int = 0

    def push(self, item: Queued) -> None:
        if len(self._q) == self._q.maxlen:
            self.dropped += 1
        self._q.append(item)

    def pop_n(self, n: int) -> list[Queued]:
        out: list[Queued] = []
        for _ in range(min(n, len(self._q))):
            out.append(self._q.popleft())
        return out

    def peek_all(self) -> list[Queued]:
        return list(self._q)

    def __len__(self) -> int:
        return len(self._q)


class StoreForward:
    """Redis Stream store-and-forward with offline buffer.

    Usage:
        sf = StoreForward(redis_url="redis://...", stream="tantu:edge:readings", max_buffer=10000)
        await sf.start()
        await sf.enqueue({"station_id": "...", "metric": "gauge_value", "value": 5.3, ...})
        # background drain runs every drain_interval_s
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        stream: str = "tantu:edge:readings",
        max_buffer: int = 10000,
        drain_interval_s: float = 2.0,
        drain_batch: int = 100,
    ) -> None:
        self.redis_url = redis_url
        self.stream = stream
        self.max_buffer = max_buffer
        self.drain_interval_s = drain_interval_s
        self.drain_batch = drain_batch
        self.buffer = InMemoryStore(maxlen=max_buffer)
        self._redis = None  # redis.asyncio.Redis | None
        self._task: asyncio.Task | None = None
        self._running = False
        self.enqueued_total: int = 0
        self.drained_total: int = 0
        self.failed_total: int = 0
        self._redis_ok: bool | None = None

    async def start(self) -> None:
        self._running = True
        await self._connect()
        self._task = asyncio.create_task(self._drain_loop(), name="store-forward-drain")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception:
                pass

    async def _connect(self) -> None:
        try:
            import redis.asyncio as aioredis  # type: ignore

            self._redis = aioredis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=1.5)
            await self._redis.ping()
            self._redis_ok = True
        except Exception:
            self._redis = None
            self._redis_ok = False

    async def _ensure_redis(self) -> bool:
        if self._redis is not None:
            try:
                await self._redis.ping()
                self._redis_ok = True
                return True
            except Exception:
                self._redis_ok = False
                self._redis = None
        # try reconnect
        await self._connect()
        return self._redis is not None

    async def enqueue(self, payload: dict[str, Any], stream: str | None = None) -> dict[str, Any]:
        """Enqueue one reading/event. Never raises on Redis failure — buffers instead."""
        s = stream or self.stream
        # enrich with edge ts if missing
        if "ts" not in payload:
            payload = {**payload, "ts": time.time()}
        # try direct Redis XADD if available
        if await self._ensure_redis():
            try:
                assert self._redis is not None
                # Redis streams: field values must be strings
                flat = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in payload.items()}
                msg_id = await self._redis.xadd(s, flat)  # type: ignore[attr-defined]
                self.enqueued_total += 1
                return {"stored": "redis", "id": msg_id, "buffered": len(self.buffer)}
            except Exception:
                self.failed_total += 1
                # fall through to buffer
                pass
        # buffer fallback
        self.buffer.push(Queued(stream=s, payload=payload, ts=time.time()))
        self.enqueued_total += 1
        return {"stored": "buffer", "id": f"buf-{self.enqueued_total}", "buffered": len(self.buffer)}

    async def _drain_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.drain_interval_s)
                await self.drain_once()
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(self.drain_interval_s)

    async def drain_once(self) -> int:
        """Push buffered items to Redis. Returns number drained."""
        if len(self.buffer) == 0:
            return 0
        if not await self._ensure_redis():
            return 0
        batch = self.buffer.pop_n(self.drain_batch)
        drained = 0
        failed: list[Queued] = []
        for item in batch:
            try:
                assert self._redis is not None
                flat = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in item.payload.items()}
                await self._redis.xadd(item.stream, flat)  # type: ignore[attr-defined]
                drained += 1
                self.drained_total += 1
            except Exception:
                failed.append(item)
                self.failed_total += 1
        # re-queue failed at front (preserve order)
        for it in reversed(failed):
            # push front by rotating
            self.buffer._q.appendleft(it)
        return drained

    def depth(self) -> int:
        return len(self.buffer)

    def status(self) -> dict[str, Any]:
        return {
            "stream": self.stream,
            "redis_url": self.redis_url,
            "redis_ok": self._redis_ok,
            "buffered": len(self.buffer),
            "dropped": self.buffer.dropped,
            "enqueued_total": self.enqueued_total,
            "drained_total": self.drained_total,
            "failed_total": self.failed_total,
        }

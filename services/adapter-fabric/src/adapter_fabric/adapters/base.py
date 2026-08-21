"""Adapter base — lifecycle, health, queue."""

from __future__ import annotations

import abc
import asyncio
import time
from typing import AsyncIterator, List, Optional

from ..domain.events import AdapterHealth, NormalizedReading, Quality
from ..domain.models import AdapterConfig
from ..infra import metrics as m


class BaseAdapter(abc.ABC):
    """Abstract adapter. Subclasses implement poll_once / streaming."""

    def __init__(self, config: AdapterConfig) -> None:
        self.config = config
        self._queue: asyncio.Queue[NormalizedReading] = asyncio.Queue(maxsize=10000)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._message_count = 0
        self._error_count = 0
        self._last_ok_ts: Optional[float] = None
        self._last_error: Optional[str] = None
        self._status = "unknown"

    @property
    def adapter_id(self) -> str:
        return self.config.adapter_id

    @property
    def protocol(self) -> str:
        return (
            self.config.protocol.value
            if hasattr(self.config.protocol, "value")
            else str(self.config.protocol)
        )

    # --- lifecycle ---
    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._status = "ok"
        await self._on_start()
        # start poll loop if poll_interval_ms > 0
        if self.config.poll_interval_ms > 0:
            self._task = asyncio.create_task(self._poll_loop(), name=f"adapter-{self.adapter_id}")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._on_stop()
        self._status = "down"
        try:
            m.ADAPTER_UP.labels(protocol=self.protocol, adapter_id=self.adapter_id).set(0)
        except Exception:
            pass

    async def health(self) -> AdapterHealth:
        return AdapterHealth(
            adapter_id=self.adapter_id,
            protocol=self.protocol,
            status=self._status,
            last_ok_ts=self._last_ok_ts,
            last_error=self._last_error,
            message_count=self._message_count,
            error_count=self._error_count,
        )

    def readings(self) -> AsyncIterator[NormalizedReading]:
        return self._queue_stream()

    async def _queue_stream(self) -> AsyncIterator[NormalizedReading]:  # type: ignore[override]
        while True:
            item = await self._queue.get()
            yield item

    async def poll_once(self) -> List[NormalizedReading]:
        """Poll once — delegated to subclass. Records metrics."""
        start = time.monotonic()
        try:
            readings = await self._poll_once_impl()
            for r in readings:
                try:
                    m.READINGS_TOTAL.labels(
                        protocol=self.protocol, adapter_id=self.adapter_id, metric=r.metric
                    ).inc()
                except Exception:
                    pass
            self._message_count += len(readings)
            self._last_ok_ts = time.time()
            self._status = "ok"
            try:
                m.ADAPTER_UP.labels(protocol=self.protocol, adapter_id=self.adapter_id).set(1)
            except Exception:
                pass
            # enqueue
            for r in readings:
                try:
                    self._queue.put_nowait(r)
                except asyncio.QueueFull:
                    # drop oldest
                    try:
                        self._queue.get_nowait()
                    except Exception:
                        pass
                    self._queue.put_nowait(r)
            return readings
        except Exception as e:
            self._error_count += 1
            self._last_error = f"{type(e).__name__}: {e}"
            self._status = "degraded" if self._last_ok_ts else "down"
            try:
                m.ERRORS_TOTAL.labels(protocol=self.protocol, adapter_id=self.adapter_id).inc()
                m.ADAPTER_UP.labels(protocol=self.protocol, adapter_id=self.adapter_id).set(0)
            except Exception:
                pass
            raise
        finally:
            try:
                m.POLL_LATENCY.labels(protocol=self.protocol, adapter_id=self.adapter_id).observe(
                    time.monotonic() - start
                )
            except Exception:
                pass

    # hooks
    async def _on_start(self) -> None:
        return None

    async def _on_stop(self) -> None:
        return None

    @abc.abstractmethod
    async def _poll_once_impl(self) -> List[NormalizedReading]: ...

    # poll loop
    async def _poll_loop(self) -> None:
        # jitter-free periodic poll
        interval = max(0.05, self.config.poll_interval_ms / 1000.0)
        while self._running:
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                break
            except Exception:
                # backoff on error
                await asyncio.sleep(min(interval * 2, 5.0))
                continue
            await asyncio.sleep(interval)

    # helper
    def _now(self) -> float:
        return time.time()

    def _reading(
        self,
        metric: str,
        value: float,
        unit: str = "",
        source_tag: str = "",
        quality: Quality = Quality.GOOD,
        raw_value: Optional[float] = None,
    ) -> NormalizedReading:
        return NormalizedReading(
            station_id=self.config.station_id,
            metric=metric,
            value=value,
            unit=unit,
            timestamp=time.time(),
            quality=quality,
            protocol=self.protocol,
            adapter_id=self.adapter_id,
            source_tag=source_tag,
            raw_value=raw_value,
        )

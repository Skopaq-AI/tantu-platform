"""Pipeline — adapter readings → normalized → NATS publish → optional defect event."""

from __future__ import annotations

import asyncio

from ..domain.events import NormalizedReading
from ..infra.nats import NatsPublisher
from ..infra import metrics as m
from .normalizer import detect_defect
from .registry import AdapterRegistry


class Pipeline:
    """Consumes readings from all adapters and publishes to NATS."""

    def __init__(self, registry: AdapterRegistry, publisher: NatsPublisher) -> None:
        self.registry = registry
        self.publisher = publisher
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        for ad in self.registry.all_adapters():
            task = asyncio.create_task(self._consume_adapter(ad), name=f"pipeline-{ad.adapter_id}")
            self._tasks.append(task)

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    async def attach_adapter(self, adapter) -> None:
        """Attach a newly registered adapter without restarting pipeline."""
        if self._running:
            task = asyncio.create_task(
                self._consume_adapter(adapter), name=f"pipeline-{adapter.adapter_id}"
            )
            self._tasks.append(task)

    async def _consume_adapter(self, adapter) -> None:
        # Prefer streaming via queue; also poll loop already enqueues.
        # We drain adapter._queue directly to avoid double buffering.
        queue = getattr(adapter, "_queue", None)
        if queue is None:
            return
        while self._running:
            try:
                reading: NormalizedReading = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            try:
                await self._handle_reading(reading)
            except Exception:
                pass

    async def _handle_reading(self, reading: NormalizedReading) -> None:
        # publish reading
        try:
            await self.publisher.publish_reading(reading)
        except Exception:
            pass
        # defect detection
        ev = detect_defect(reading)
        if ev is not None:
            try:
                await self.publisher.publish(ev)
                m.DEFECTS_TOTAL.labels(
                    protocol=reading.protocol, defect_class=ev.defect_class.value
                ).inc()
            except Exception:
                pass

    # For tests: process one reading synchronously
    async def process_one(self, reading: NormalizedReading) -> None:
        await self._handle_reading(reading)

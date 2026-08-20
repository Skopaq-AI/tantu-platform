"""NATS publisher — real nats-py, graceful fallback to in-memory when NATS unavailable."""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from typing import Optional

from ..domain.events import DefectEvent, NormalizedReading

try:
    import nats  # type: ignore

    _HAS_NATS = True
except Exception:
    _HAS_NATS = False


def _event_to_json(ev: DefectEvent) -> bytes:
    d = {
        "station_id": ev.station_id,
        "track": ev.track.value if hasattr(ev.track, "value") else str(ev.track),
        "defect_class": ev.defect_class.value if hasattr(ev.defect_class, "value") else str(ev.defect_class),
        "confidence": ev.confidence,
        "latency_ms": ev.latency_ms,
        "timestamp": ev.timestamp,
        "protocol": ev.protocol,
        "adapter_id": ev.adapter_id,
    }
    return json.dumps(d).encode()


def _reading_to_json(r: NormalizedReading) -> bytes:
    d = {
        "station_id": r.station_id,
        "metric": r.metric,
        "value": r.value,
        "unit": r.unit,
        "timestamp": r.timestamp,
        "quality": r.quality.value if hasattr(r.quality, "value") else str(r.quality),
        "protocol": r.protocol,
        "adapter_id": r.adapter_id,
        "source_tag": r.source_tag,
    }
    return json.dumps(d).encode()


class NatsPublisher:
    """Publishes DefectEvent / NormalizedReading to NATS JetStream or core NATS.

    Topics:
      tantu.events.defect  -> DefectEvent
      tantu.telemetry.<metric> -> NormalizedReading
    """

    def __init__(self, url: Optional[str] = None) -> None:
        self.url = url or os.getenv("NATS_URL", "nats://localhost:4222")
        self._nc = None
        self._js = None
        self._lock = asyncio.Lock()
        self._published: list[bytes] = []  # in-memory fallback for tests / offline

    async def connect(self) -> None:
        if not _HAS_NATS:
            return
        try:
            self._nc = await nats.connect(self.url)  # type: ignore[attr-defined]
            try:
                self._js = self._nc.jetstream()  # type: ignore[attr-defined]
            except Exception:
                self._js = None
        except Exception:
            # stay in fallback mode
            self._nc = None
            self._js = None

    async def close(self) -> None:
        if self._nc:
            try:
                await self._nc.drain()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._nc = None
            self._js = None

    async def publish(self, event: DefectEvent) -> None:
        data = _event_to_json(event)
        subject = "tantu.events.defect"
        await self._publish(subject, data)

    async def publish_reading(self, reading: NormalizedReading) -> None:
        data = _reading_to_json(reading)
        subject = f"tantu.telemetry.{reading.metric}"
        await self._publish(subject, data)

    async def _publish(self, subject: str, data: bytes) -> None:
        async with self._lock:
            self._published.append(data)
        if self._nc is not None:
            try:
                if self._js is not None:
                    try:
                        await self._js.publish(subject, data)  # type: ignore[attr-defined]
                        return
                    except Exception:
                        pass
                await self._nc.publish(subject, data)  # type: ignore[attr-defined]
            except Exception:
                # keep fallback
                pass

    # for tests
    @property
    def published_events(self) -> list[bytes]:
        return list(self._published)


# Global singleton holder (set by api.main lifespan)
_publisher: Optional[NatsPublisher] = None


def get_publisher() -> NatsPublisher:
    global _publisher
    if _publisher is None:
        _publisher = NatsPublisher()
    return _publisher


def set_publisher(p: NatsPublisher) -> None:
    global _publisher
    _publisher = p

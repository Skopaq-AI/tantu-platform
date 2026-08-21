"""NATS bus — subscriber for derived events, publisher for reports."""

from __future__ import annotations

import json
import logging
from typing import Callable, Awaitable, Optional

from ..domain.events import DefectEvent, DefectClass, Track
from .config import settings

log = logging.getLogger("orchestrator.nats")

# Type for handler
EventHandler = Callable[[DefectEvent], Awaitable[None]]


class NatsBus:
    def __init__(self, url: Optional[str] = None):
        self.url = url or settings.nats_url
        self._nc: Optional[object] = None
        self._js = None
        self._subs: list[object] = []
        self._handler: Optional[EventHandler] = None

    async def connect(self) -> bool:
        try:
            import nats  # type: ignore

            self._nc = await nats.connect(self.url, connect_timeout=3, max_reconnect_attempts=3)
            log.info("orchestrator NATS connected to %s", self.url)
            return True
        except Exception as e:
            log.warning("orchestrator NATS unavailable %s: %s", self.url, e)
            self._nc = None
            return False

    async def subscribe(self, handler: EventHandler, subjects: Optional[list[str]] = None) -> None:
        self._handler = handler
        if self._nc is None:
            connected = await self.connect()
            if not connected:
                log.warning("orchestrator NATS subscribe skipped — no connection")
                return
        subjects = subjects or settings.nats_subjects_list
        assert self._nc is not None
        for subj in subjects:
            try:
                cb = self._make_callback(handler)
                sub = await self._nc.subscribe(subj, cb=cb)  # type: ignore[attr-defined]
                self._subs.append(sub)
                log.info("orchestrator NATS subscribed to %s", subj)
            except Exception as e:
                log.warning("NATS subscribe %s failed: %s", subj, e)

    def _make_callback(self, handler: EventHandler):
        async def _cb(msg):
            try:
                data = json.loads(msg.data.decode())
                ev = _parse_event(data)
                if ev is None:
                    log.debug("NATS skip unparseable: %s", data)
                    return
                await handler(ev)
            except Exception as e:
                log.warning("NATS handler error: %s", e)

        return _cb

    async def publish_report(self, subject: Optional[str], payload: dict) -> None:
        if self._nc is None:
            log.debug("NATS publish skipped — not connected")
            return
        try:
            subj = subject or settings.nats_report_subject
            data = json.dumps(payload).encode()
            await self._nc.publish(subj, data)  # type: ignore[attr-defined]
            log.info("orchestrator published report to %s", subj)
        except Exception as e:
            log.warning("NATS publish failed: %s", e)

    async def close(self) -> None:
        for sub in self._subs:
            try:
                await sub.unsubscribe()  # type: ignore[attr-defined]
            except Exception:
                pass
        self._subs.clear()
        if self._nc is not None:
            try:
                await self._nc.close()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._nc = None


def _parse_event(data: dict) -> Optional[DefectEvent]:
    """Coerce JSON dict into DefectEvent — tolerant of upstream shapes."""
    try:
        station_id = data.get("station_id") or data.get("stationId") or "unknown"
        defect_raw = data.get("defect_class") or data.get("defectClass") or "none"
        # handle nested? Some producers use defect_class string directly
        try:
            klass = DefectClass(defect_raw)
        except ValueError:
            klass = DefectClass.NONE
        conf = float(data.get("confidence", 0.9))
        latency = float(data.get("latency_ms", data.get("latencyMs", 22.0)))
        proto = data.get("protocol", "unknown")
        plant_id = data.get("plant_id", data.get("plantId", "plant-demo-01"))
        event_id = data.get("event_id", data.get("eventId", None))
        track_raw = data.get("track", "line")
        try:
            track = Track(track_raw)
        except ValueError:
            track = Track.LINE
        ts = data.get("timestamp")
        if ts is None:
            import time

            ts = time.time()
        else:
            ts = float(ts)
        return DefectEvent(
            station_id=str(station_id),
            track=track,
            defect_class=klass,
            confidence=conf,
            latency_ms=latency,
            timestamp=ts,
            protocol=str(proto),
            plant_id=str(plant_id),
            event_id=str(event_id) if event_id else __import__("uuid").uuid4().hex,
            adapter_id=str(data.get("adapter_id", "")),
        )
    except Exception:
        return None


nats_bus = NatsBus()

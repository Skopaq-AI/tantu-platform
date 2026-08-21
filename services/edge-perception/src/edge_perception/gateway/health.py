"""Health aggregation — tiered health view for /health."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class ComponentHealth:
    name: str
    status: str  # ok | degraded | down | unknown
    latency_ms: float | None = None
    last_ok_ts: float | None = None
    last_error: str | None = None
    details: dict = field(default_factory=dict)


class HealthAggregator:
    def __init__(self) -> None:
        self._components: dict[str, ComponentHealth] = {}

    def set(self, comp: ComponentHealth) -> None:
        self._components[comp.name] = comp

    def mark_ok(
        self, name: str, latency_ms: float | None = None, details: dict | None = None
    ) -> None:
        now = time.time()
        prev = self._components.get(name)
        self._components[name] = ComponentHealth(
            name=name,
            status="ok",
            latency_ms=latency_ms,
            last_ok_ts=now,
            last_error=None
            if (prev and prev.status != "down")
            else (prev.last_error if prev else None),
            details=details or {},
        )

    def mark_degraded(self, name: str, reason: str) -> None:
        prev = self._components.get(name)
        self._components[name] = ComponentHealth(
            name=name,
            status="degraded",
            latency_ms=prev.latency_ms if prev else None,
            last_ok_ts=prev.last_ok_ts if prev else None,
            last_error=reason,
            details=prev.details if prev else {},
        )

    def mark_down(self, name: str, reason: str) -> None:
        prev = self._components.get(name)
        self._components[name] = ComponentHealth(
            name=name,
            status="down",
            latency_ms=None,
            last_ok_ts=prev.last_ok_ts if prev else None,
            last_error=reason,
            details=prev.details if prev else {},
        )

    def overall(self) -> str:
        if not self._components:
            return "unknown"
        statuses = {c.status for c in self._components.values()}
        if "down" in statuses:
            return "degraded" if len(statuses) > 1 else "down"
        if "degraded" in statuses:
            return "degraded"
        if statuses == {"ok"}:
            return "ok"
        return "unknown"

    def snapshot(self) -> dict:
        return {
            "status": self.overall(),
            "ts": time.time(),
            "frames_never_leave": True,
            "components": {
                k: {
                    "status": v.status,
                    "latency_ms": v.latency_ms,
                    "last_ok_ts": v.last_ok_ts,
                    "last_error": v.last_error,
                    "details": v.details,
                }
                for k, v in self._components.items()
            },
        }

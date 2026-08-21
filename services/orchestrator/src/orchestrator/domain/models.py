"""Domain models for persistence view — not ORM, just value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PersistedEvent:
    event_id: str
    plant_id: str
    station_id: str
    defect_class: str
    confidence: float
    latency_ms: float
    protocol: str
    ts: float


@dataclass(frozen=True, slots=True)
class PersistedReport:
    id: str
    plant_id: str
    summary: str
    contributing: list[str]
    confidence: float
    tokens_in: int
    tokens_out: int
    cost_usd: float
    created_at: float

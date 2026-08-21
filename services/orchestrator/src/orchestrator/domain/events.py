"""Domain events — ubiquitous language. Pure, no I/O. No image field by construction."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from time import time
from typing import Optional


class Track(str, Enum):
    FAB = "fab"
    LINE = "line"


class DefectClass(str, Enum):
    NONE = "none"
    PRESSURE_DRIFT = "pressure_drift"
    VIB_HIGH = "vib_high"
    THERMAL_HIGH = "thermal_high"
    SOLDER_VOID = "solder_void"
    ALIGNMENT_DRIFT = "alignment_drift"


@dataclass(frozen=True, slots=True)
class DefectEvent:
    """Derived only — no image_bytes, no frame. Type-system prevents raw frames leaking to reasoning."""

    station_id: str
    track: Track
    defect_class: DefectClass
    confidence: float  # 0..1
    latency_ms: float
    timestamp: float = field(default_factory=time)
    protocol: str = "unknown"
    plant_id: str = "plant-demo-01"
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    adapter_id: str = ""

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0..1, got {self.confidence}")

    @property
    def is_fault(self) -> bool:
        return self.defect_class != DefectClass.NONE

    def dedupe_key(self) -> str:
        """Stable key for idempotency — event_id preferred, else content hash."""
        return self.event_id


@dataclass(frozen=True, slots=True)
class TelemetryReading:
    station_id: str
    metric: str
    value: float
    unit: str
    timestamp: float = field(default_factory=time)
    plant_id: str = "plant-demo-01"


@dataclass(frozen=True, slots=True)
class CorrelationReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    plant_id: str = "plant-demo-01"
    summary: str = ""
    contributing: list[str] = field(default_factory=list)
    confidence: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    created_at: float = field(default_factory=time)
    window_size: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def make_event(
    station: str = "line2-cluster1-gauge3",
    defect: DefectClass = DefectClass.NONE,
    conf: float = 0.95,
    proto: str = "opcua",
    plant_id: str = "plant-demo-01",
    event_id: Optional[str] = None,
) -> DefectEvent:
    import random

    return DefectEvent(
        station_id=station,
        track=Track.LINE,
        defect_class=defect,
        confidence=conf,
        latency_ms=random.uniform(18, 39),
        protocol=proto,
        plant_id=plant_id,
        event_id=event_id or uuid.uuid4().hex,
    )

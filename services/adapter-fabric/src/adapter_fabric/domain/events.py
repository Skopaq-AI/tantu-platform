"""Domain events — pure, no I/O. No image field by construction."""
from __future__ import annotations

from dataclasses import dataclass, field
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


class Quality(str, Enum):
    GOOD = "good"
    UNCERTAIN = "uncertain"
    BAD = "bad"


@dataclass(frozen=True, slots=True)
class DefectEvent:
    """Derived only — no image_bytes, no frame. Enforced by type.

    Deliberately omits any image/frame/bytes field so the type-system
    prevents raw frames from reaching the reasoning plane.
    """

    station_id: str
    track: Track
    defect_class: DefectClass
    confidence: float  # 0-1
    latency_ms: float
    timestamp: float = field(default_factory=time)
    protocol: str = "unknown"
    adapter_id: str = ""


@dataclass(frozen=True, slots=True)
class TelemetryReading:
    station_id: str
    metric: str  # vibration_rms | bearing_temp_c | pressure_bar | gauge_value
    value: float
    unit: str
    timestamp: float = field(default_factory=time)


@dataclass(frozen=True, slots=True)
class NormalizedReading:
    """Single canonical schema all adapters normalize to."""

    station_id: str
    metric: str
    value: float
    unit: str
    timestamp: float = field(default_factory=time)
    quality: Quality = Quality.GOOD
    protocol: str = "unknown"
    adapter_id: str = ""
    source_tag: str = ""
    raw_value: Optional[float] = None


@dataclass(frozen=True, slots=True)
class CorrelationReport:
    summary: str
    contributing: list[str]
    confidence: float
    tokens_in: int
    tokens_out: int
    cost_usd: float


@dataclass(frozen=True, slots=True)
class AdapterHealth:
    adapter_id: str
    protocol: str
    status: str  # ok | degraded | down | unknown
    last_ok_ts: Optional[float] = None
    last_error: Optional[str] = None
    message_count: int = 0
    error_count: int = 0


def make_event(
    station: str = "line2-cluster1-gauge3",
    defect: DefectClass = DefectClass.NONE,
    conf: float = 0.95,
    proto: str = "opcua",
) -> DefectEvent:
    import random

    return DefectEvent(
        station_id=station,
        track=Track.LINE,
        defect_class=defect,
        confidence=conf,
        latency_ms=random.uniform(18, 39),
        protocol=proto,
    )

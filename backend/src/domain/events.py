"""Domain — ubiquitous language. No image field → raw frames cannot flow."""
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

@dataclass(frozen=True, slots=True)
class DefectEvent:
    """Derived only — no image_bytes, no frame. Enforced by type."""
    station_id: str
    track: Track
    defect_class: DefectClass
    confidence: float  # 0-1
    latency_ms: float
    timestamp: float = field(default_factory=time)
    protocol: str = "unknown"  # opcua | modbus | camera | mqtt | ...

@dataclass(frozen=True, slots=True)
class TelemetryReading:
    station_id: str
    metric: str  # vibration_rms | bearing_temp_c | pressure_bar | gauge_value
    value: float
    unit: str
    timestamp: float = field(default_factory=time)

@dataclass(frozen=True, slots=True)
class CorrelationReport:
    summary: str
    contributing: list[str]
    confidence: float
    tokens_in: int
    tokens_out: int
    cost_usd: float

# Factory helper for tests
def make_event(station="line2-cluster1-gauge3", defect=DefectClass.NONE, conf=0.95, proto="opcua"):
    import random
    return DefectEvent(station_id=station, track=Track.LINE, defect_class=defect, confidence=conf, latency_ms=random.uniform(18,39), protocol=proto)

"""Normalizer — ensures readings conform to canonical schema and optionally derives defects."""

from __future__ import annotations

from typing import Optional

from ..domain.events import DefectClass, DefectEvent, NormalizedReading, Quality, Track


# Simple threshold-based defect detection from reading value.
# Real system would use ML; here we provide deterministic rules for demo/tests.
def detect_defect(reading: NormalizedReading) -> Optional[DefectEvent]:
    metric = reading.metric.lower()
    v = reading.value
    cls: Optional[DefectClass] = None
    conf = 0.0

    if "pressure" in metric:
        if v > 8.5:
            cls = DefectClass.PRESSURE_DRIFT
            conf = min(0.95, 0.6 + (v - 8.5) * 0.1)
        elif v < 1.0:
            cls = DefectClass.PRESSURE_DRIFT
            conf = 0.65
    elif "vib" in metric or "vibration" in metric:
        if v > 7.0:
            cls = DefectClass.VIB_HIGH
            conf = min(0.96, 0.55 + (v - 7.0) * 0.08)
    elif "temp" in metric or "thermal" in metric:
        if v > 85:
            cls = DefectClass.THERMAL_HIGH
            conf = min(0.97, 0.6 + (v - 85) * 0.02)
    elif "gauge" in metric:
        # gauge too high/low
        if v > 90:
            cls = DefectClass.PRESSURE_DRIFT
            conf = 0.72
        elif v < 10:
            cls = DefectClass.PRESSURE_DRIFT
            conf = 0.68

    if cls is None:
        return None
    # track heuristic: fab metrics vs line
    track = Track.FAB if "fab" in reading.station_id.lower() else Track.LINE
    return DefectEvent(
        station_id=reading.station_id,
        track=track,
        defect_class=cls,
        confidence=conf,
        latency_ms=5.0,
        protocol=reading.protocol,
        adapter_id=reading.adapter_id,
    )


def normalize_quality(q: str) -> Quality:
    try:
        return Quality(q.lower())
    except Exception:
        return Quality.GOOD

"""Pydantic schemas — I/O for edge-perception. No raw frames leave the plant by contract."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GaugeInferIn(BaseModel):
    station_id: str = Field(examples=["line2-cluster1-gauge3"])
    image_b64: str = Field(description="Base64-encoded JPEG/PNG image of gauge face")
    min_value: float = 0.0
    max_value: float = 10.0
    min_angle_deg: float = 135.0
    max_angle_deg: float = 45.0
    quality_gate: bool = True


class GaugeInferOut(BaseModel):
    station_id: str
    metric: str = "gauge_value"
    value: float
    unit: str = "bar"
    angle_deg: float
    confidence: float
    quality: Literal["good", "uncertain", "bad"]
    latency_ms: float
    centre: tuple[int, int]
    radius: int
    tier: str
    timestamp: float
    debug: dict[str, Any] = {}


class VibrationInferIn(BaseModel):
    station_id: str
    samples: list[float] = Field(description="Accelerometer window, e.g. 1024 samples")
    sample_rate_hz: float
    shaft_freq_hz: float | None = None
    unit: str = "mm/s"


class VibrationInferOut(BaseModel):
    station_id: str
    metric: str = "vibration_rms"
    rms: float
    unit: str
    peak_freqs: list[float]
    peak_mags: list[float]
    dominant_freq: float
    crest_factor: float
    kurtosis: float
    band_energies: dict[str, float]
    health: Literal["ok", "watch", "alarm"]
    latency_ms: float
    n_samples: int
    sample_rate_hz: float
    tier: str
    timestamp: float


class ThermalReadIn(BaseModel):
    probe_id: str = "probe-01"
    raw: float | None = Field(
        default=None, description="Inject raw value (test); if None, reads 1-Wire"
    )
    calibrate_two_point: dict | None = None  # {raw_low, ref_low, raw_high, ref_high}


class ThermalOut(BaseModel):
    probe_id: str
    raw: float
    value: float
    unit: str
    quality: Literal["good", "uncertain", "bad"]
    latency_ms: float
    timestamp: float
    tier: str
    notes: list[str] = []


class CTInferIn(BaseModel):
    station_id: str
    samples: list[float] = Field(description="CT current in Amps")
    sample_rate_hz: float
    mains_hz: float = 50.0


class CTOut(BaseModel):
    station_id: str
    rms_a: float
    peak_a: float
    thd_percent: float
    fundamental_hz: float
    signature: str
    harmonics: dict[int, float]
    power_proxy_w: float
    quality: str
    latency_ms: float
    tier: str
    timestamp: float


class OTAStageIn(BaseModel):
    version: str
    sha256: str
    signature_b64: str = ""
    artifact_b64: str = ""  # base64 artifact bytes (optional, for testing without URL)
    artifact_url: str = ""
    notes: str = ""


class HealthOut(BaseModel):
    status: str
    ts: float
    tier: str
    tier_caps: dict[str, Any]
    components: dict[str, Any]
    store_forward: dict[str, Any]
    ota: dict[str, Any]

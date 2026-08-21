"""Pydantic models — request/response schemas."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Lang(str, Enum):
    en = "en"
    hi = "hi"
    ta = "ta"
    te = "te"
    kn = "kn"


class DefectClass(str, Enum):
    none = "none"
    pressure_drift = "pressure_drift"
    vib_high = "vib_high"
    thermal_high = "thermal_high"
    solder_void = "solder_void"
    alignment_drift = "alignment_drift"


class Track(str, Enum):
    fab = "fab"
    line = "line"


class DefectEventIn(BaseModel):
    station_id: str = Field(..., examples=["line2-cluster1-gauge3"])
    track: Track = Track.line
    defect_class: DefectClass = DefectClass.none
    confidence: float = Field(0.9, ge=0, le=1)
    latency_ms: float = 22.5
    protocol: str = Field("opcua", examples=["opcua", "modbus", "camera", "mqtt"])
    timestamp: Optional[float] = None


class AskIn(BaseModel):
    question: str = Field(
        ..., min_length=3, max_length=2000, examples=["Why is Line 2 vibration high?"]
    )
    plant_id: str = Field("plant-demo-01")
    lang: Lang = Lang.en
    air_gapped: bool = False
    top_k: int = Field(3, ge=1, le=10)
    prompt_version: str = Field("ask_v1", examples=["ask_v1", "ask_v2"])


class AskOut(BaseModel):
    answer: str
    vernacular: str
    lang: Lang
    citations: List[dict]
    grounded: bool
    backend: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    air_gapped: bool
    prompt_version: str


class CorrelateIn(BaseModel):
    events: List[DefectEventIn] = Field(..., min_length=1, max_length=50)
    plant_id: str = "plant-demo-01"
    lang: Lang = Lang.en
    air_gapped: bool = False
    top_k: int = Field(5, ge=1, le=10)
    prompt_version: str = Field("correlate_v1", examples=["correlate_v1", "correlate_v2"])


class CorrelateOut(BaseModel):
    summary: str
    summary_vernacular: str
    contributing: List[str]
    confidence: float
    citations: List[dict]
    grounded: bool
    backend: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    air_gapped: bool
    prompt_version: str


class RagIngestIn(BaseModel):
    id: str = Field(..., examples=["runbook-press-01"])
    text: str = Field(
        ..., min_length=10, examples=["Line 2 pressure high: check valve 3, max 8 bar per runbook."]
    )
    metadata: dict = Field(default_factory=dict)


class RagSearchIn(BaseModel):
    query: str
    top_k: int = Field(3, ge=1, le=10)


class TtsIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    lang: Lang = Lang.en


class SttIn(BaseModel):
    audio_base64: str
    lang: Lang = Lang.en

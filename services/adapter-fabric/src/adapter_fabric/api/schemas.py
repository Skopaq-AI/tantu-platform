"""Pydantic schemas for API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TagMappingIn(BaseModel):
    source_tag: str
    metric: str
    unit: str = ""
    scale: float = 1.0
    offset: float = 0.0
    data_type: str = "float"
    compound_formula: Optional[str] = None
    source_tags: Optional[Dict[str, str]] = None


class AdapterConfigIn(BaseModel):
    adapter_id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-_]{1,63}$")
    protocol: str = Field(..., description="opcua | modbus | mqtt | mtconnect | ethernet_ip | camera")
    station_id: str
    enabled: bool = True
    tags: List[TagMappingIn] = Field(default_factory=list)
    params: Dict[str, Any] = Field(default_factory=dict)
    poll_interval_ms: int = 1000


class AdapterConfigOut(BaseModel):
    adapter_id: str
    protocol: str
    station_id: str
    enabled: bool
    tags: List[TagMappingIn]
    params: Dict[str, Any]
    poll_interval_ms: int
    status: str = "unknown"


class HealthOut(BaseModel):
    status: str
    service: str = "adapter-fabric"
    version: str = "0.1.0"
    adapters: List[Dict[str, Any]] = Field(default_factory=list)
    nats_connected: bool = False


class ReadingOut(BaseModel):
    station_id: str
    metric: str
    value: float
    unit: str
    timestamp: float
    quality: str
    protocol: str
    adapter_id: str
    source_tag: str


class DefectEventOut(BaseModel):
    station_id: str
    track: str
    defect_class: str
    confidence: float
    latency_ms: float
    timestamp: float
    protocol: str
    adapter_id: str


class IngestReadingIn(BaseModel):
    station_id: str
    metric: str
    value: float
    unit: str = ""
    protocol: str = "unknown"
    adapter_id: str = ""
    source_tag: str = ""


class TokenIn(BaseModel):
    sub: str = "operator"
    plant_id: str = "plant-demo-01"
    role: str = "engineer"
    exp_min: int = 60

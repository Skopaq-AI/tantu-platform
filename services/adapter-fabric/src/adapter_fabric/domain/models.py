"""Domain models — tag maps, normalization config, compounding."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Protocol(str, Enum):
    OPCUA = "opcua"
    MODBUS = "modbus"
    MQTT = "mqtt"
    MTCONNECT = "mtconnect"
    ETHERNET_IP = "ethernet_ip"
    CAMERA = "camera"


@dataclass(frozen=True, slots=True)
class TagMapping:
    """One row of a tag-map. Source-address → canonical metric.

    compounding: optional formula that combines multiple source tags.
    Examples:
      scale/offset            -> value = raw*scale + offset
      compound_formula = "(pressure_raw * 0.1) + 5"
      multi-tag: {"pressure_raw": "ns=2;i=1001", "temp_raw": "ns=2;i=1002"} + formula
    """

    source_tag: str  # protocol-specific address (nodeId, register, topic, dataItemId, tag name)
    metric: str  # canonical metric name
    unit: str = ""
    scale: float = 1.0
    offset: float = 0.0
    data_type: str = "float"  # float | int16 | uint16 | int32 | uint32 | float32 | bool
    compound_formula: Optional[str] = None  # if set, evaluate over raw dict
    source_tags: Optional[dict[str, str]] = None  # for multi-tag compounds: {var: source_tag}


@dataclass(frozen=True, slots=True)
class AdapterConfig:
    adapter_id: str
    protocol: Protocol
    station_id: str
    enabled: bool = True
    tags: tuple[TagMapping, ...] = ()
    # protocol-specific freeform (endpoint, host, topics, calibration…)
    params: dict[str, Any] = field(default_factory=dict)
    poll_interval_ms: int = 1000


@dataclass(frozen=True, slots=True)
class NormalizedSchema:
    """Documents the canonical shape; used for OpenAPI / validation tests."""

    required_fields: tuple[str, ...] = (
        "station_id",
        "metric",
        "value",
        "unit",
        "timestamp",
        "quality",
        "protocol",
    )
    allowed_quality: tuple[str, ...] = ("good", "uncertain", "bad")
    allowed_protocol: tuple[str, ...] = (
        "opcua",
        "modbus",
        "mqtt",
        "mtconnect",
        "ethernet_ip",
        "camera",
    )

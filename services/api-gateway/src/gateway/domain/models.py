"""Domain models — ubiquitous language for gateway."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated caller — projection of JWT claims."""

    sub: str
    plant_id: str
    role: str
    scopes: tuple[str, ...] = ()
    extra: dict = field(default_factory=dict)  # device_id, plant_ids, etc.


@dataclass(frozen=True, slots=True)
class Resource:
    """Resource being accessed — RBAC + ABAC input."""

    service: str  # adapter-fabric | orchestrator | reasoning-copilot | edge-perception | gateway
    path: str  # /api/v1/events, /health, etc.
    action: str  # read | write | post | delete | health | *
    plant_id: Optional[str] = None  # ABAC attribute — must equal principal.plant_id unless wildcard
    method: str = "GET"


@dataclass(frozen=True, slots=True)
class DownstreamService:
    name: str
    base_url: str
    health_path: str = "/health"
    timeout_s: float = 5.0


@dataclass(frozen=True, slots=True)
class AuditEntry:
    request_id: str
    principal: Optional[str]
    plant_id: Optional[str]
    method: str
    path: str
    status: int
    latency_ms: float
    decision: str  # allow | deny | error
    reason: str = ""

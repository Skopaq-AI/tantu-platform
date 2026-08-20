"""Proxy service — maps incoming /api paths to downstream bases."""
from __future__ import annotations

from typing import Optional

from ..infra.config import settings


# Explicit prefix → downstream name mapping (first match wins)
ROUTE_TABLE: list[tuple[str, str]] = [
    ("/api/v1/ingest", "adapter-fabric"),
    ("/api/v1/telemetry", "adapter-fabric"),
    ("/api/v1/adapters", "adapter-fabric"),
    ("/api/v1/events", "orchestrator"),
    ("/api/v1/correlation-reports", "orchestrator"),
    ("/api/v1/reports", "orchestrator"),
    ("/api/v1/window", "orchestrator"),
    ("/api/v1/reasoning", "reasoning-copilot"),
    ("/api/v1/ask", "reasoning-copilot"),
    ("/api/v1/rag", "reasoning-copilot"),
    ("/api/v1/vernacular", "reasoning-copilot"),
    ("/api/v1/edge", "edge-perception"),
    ("/api/v1/perception", "edge-perception"),
    # generic /api/{service}
    ("/api/adapter-fabric", "adapter-fabric"),
    ("/api/orchestrator", "orchestrator"),
    ("/api/reasoning-copilot", "reasoning-copilot"),
    ("/api/reasoning", "reasoning-copilot"),
    ("/api/edge-perception", "edge-perception"),
    ("/api/edge", "edge-perception"),
]


def resolve_downstream(path: str) -> Optional[str]:
    """Return base URL for path or None if unknown."""
    for prefix, service_name in ROUTE_TABLE:
        if path.startswith(prefix):
            base = settings.downstream_services.get(service_name)
            if base:
                return base
    # fallback: try generic /api/{service}/...
    if path.startswith("/api/"):
        parts = path.split("/")
        if len(parts) >= 3:
            svc = parts[2]
            base = settings.downstream_services.get(svc)
            if base:
                return base
    return None

"""FastAPI service — adapter-fabric on :8001. Hexagonal entry point."""
from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ..application.registry import AdapterRegistry
from ..application.pipeline import Pipeline
from ..application.normalizer import detect_defect
from ..domain.events import DefectEvent, DefectClass, Track, NormalizedReading, Quality
from ..domain.models import AdapterConfig, TagMapping, Protocol
from ..infra.logging import configure_logging, get_logger
from ..infra.nats import NatsPublisher, get_publisher, set_publisher
from ..infra.security import require_auth, optional_auth, issue_jwt
from ..infra import metrics as prom
from ..infra.telemetry import configure_tracing
from .schemas import (
    AdapterConfigIn,
    AdapterConfigOut,
    HealthOut,
    ReadingOut,
    DefectEventOut,
    IngestReadingIn,
    TokenIn,
    TagMappingIn,
)
from .deps import get_registry, get_nats, set_registry

configure_logging()
logger = get_logger("adapter_fabric.api")
try:
    tracer = configure_tracing()
except Exception:
    tracer = None  # type: ignore

# Globals for lifespan
_pipeline: Optional[Pipeline] = None
_registry_global: AdapterRegistry = AdapterRegistry()
_publisher_global: NatsPublisher = NatsPublisher()
set_registry(_registry_global)
set_publisher(_publisher_global)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    # startup
    try:
        await _publisher_global.connect()
    except Exception as e:
        logger.warning("nats.connect failed", error=str(e))
    # pipeline will attach to adapters as they are registered; start empty
    global _pipeline
    _pipeline = Pipeline(_registry_global, _publisher_global)
    await _pipeline.start()
    logger.info("adapter-fabric started", port=8001)
    yield
    # shutdown
    if _pipeline:
        await _pipeline.stop()
    await _registry_global.stop_all()
    await _publisher_global.close()


app = FastAPI(
    title="TANTU Adapter Fabric",
    version="0.1.0",
    description="Multi-protocol shopfloor ingestion — OPC-UA, Modbus, MQTT, MTConnect, EtherNet/IP, Camera — normalized to one schema, derived DefectEvents only (no image field).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _to_adapter_config(inp: AdapterConfigIn) -> AdapterConfig:
    try:
        proto = Protocol(inp.protocol.lower())
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Unknown protocol: {inp.protocol}. Allowed: {[p.value for p in Protocol]}")
    tags = tuple(
        TagMapping(
            source_tag=t.source_tag,
            metric=t.metric,
            unit=t.unit,
            scale=t.scale,
            offset=t.offset,
            data_type=t.data_type,
            compound_formula=t.compound_formula,
            source_tags=t.source_tags,
        )
        for t in inp.tags
    )
    return AdapterConfig(
        adapter_id=inp.adapter_id,
        protocol=proto,
        station_id=inp.station_id,
        enabled=inp.enabled,
        tags=tags,
        params=dict(inp.params),
        poll_interval_ms=inp.poll_interval_ms,
    )


def _reading_to_out(r: NormalizedReading) -> Dict[str, Any]:
    return {
        "station_id": r.station_id,
        "metric": r.metric,
        "value": r.value,
        "unit": r.unit,
        "timestamp": r.timestamp,
        "quality": r.quality.value if hasattr(r.quality, "value") else str(r.quality),
        "protocol": r.protocol,
        "adapter_id": r.adapter_id,
        "source_tag": r.source_tag,
    }


# ---------------------------------------------------------------------------
# health / metrics / openapi
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"], summary="Health — adapter statuses + NATS")
async def health():
    adapters = await _registry_global.health_all()
    nats_ok = getattr(_publisher_global, "_nc", None) is not None
    overall = "ok" if all(a.get("status") in ("ok", "unknown") or a.get("status") == "ok" for a in adapters) or not adapters else "degraded"
    # if no adapters, ok
    if not adapters:
        overall = "ok"
    return {"status": overall, "service": "adapter-fabric", "version": "0.1.0", "adapters": adapters, "nats_connected": bool(nats_ok), "ts": time.time()}


@app.get("/metrics", tags=["ops"], summary="Prometheus metrics")
async def metrics():
    data = prom.generate_latest()  # type: ignore
    return Response(content=data, media_type=prom.CONTENT_TYPE_LATEST)


@app.get("/info", tags=["ops"])
async def info():
    return {
        "name": "adapter-fabric",
        "version": "0.1.0",
        "protocols": [p.value for p in Protocol],
        "canonical_schema": ["station_id", "metric", "value", "unit", "timestamp", "quality", "protocol", "adapter_id", "source_tag"],
        "frames_never_leave": True,
        "defect_event_has_no_image_field": True,
    }


# ---------------------------------------------------------------------------
# auth — token issuance (for demos) + protected example
# ---------------------------------------------------------------------------
@app.post("/auth/token", tags=["auth"], summary="Issue JWT (demo)")
async def auth_token(body: TokenIn):
    tok = issue_jwt(sub=body.sub, plant_id=body.plant_id, role=body.role, exp_min=body.exp_min)
    return {"access_token": tok, "token_type": "bearer", "claims": {"sub": body.sub, "plant_id": body.plant_id, "role": body.role}}


# ---------------------------------------------------------------------------
# adapter registry CRUD
# ---------------------------------------------------------------------------
@app.post("/adapters", tags=["adapters"], summary="Register / upsert adapter")
async def register_adapter(body: AdapterConfigIn, claims: dict = Depends(require_auth)):
    cfg = _to_adapter_config(body)
    adapter = await _registry_global.register(cfg)
    # attach to pipeline if running
    if _pipeline and _pipeline._running:
        await _pipeline.attach_adapter(adapter)
    logger.info("adapter registered", adapter_id=cfg.adapter_id, protocol=cfg.protocol.value)
    return {"adapter_id": adapter.adapter_id, "protocol": adapter.protocol, "station_id": cfg.station_id, "status": (await adapter.health()).status}


@app.get("/adapters", tags=["adapters"], summary="List adapters")
async def list_adapters(claims: dict = Depends(optional_auth)):
    out: List[Dict[str, Any]] = []
    for ad in _registry_global.all_adapters():
        h = await ad.health()
        cfg = ad.config
        out.append(
            {
                "adapter_id": cfg.adapter_id,
                "protocol": cfg.protocol.value if hasattr(cfg.protocol, "value") else str(cfg.protocol),
                "station_id": cfg.station_id,
                "enabled": cfg.enabled,
                "poll_interval_ms": cfg.poll_interval_ms,
                "tags": [{"source_tag": t.source_tag, "metric": t.metric, "unit": t.unit, "scale": t.scale, "offset": t.offset, "data_type": t.data_type, "compound_formula": t.compound_formula, "source_tags": t.source_tags} for t in cfg.tags],
                "params": cfg.params,
                "health": {"status": h.status, "last_ok_ts": h.last_ok_ts, "last_error": h.last_error, "message_count": h.message_count, "error_count": h.error_count},
            }
        )
    return out


@app.get("/adapters/{adapter_id}", tags=["adapters"])
async def get_adapter(adapter_id: str):
    ad = await _registry_global.get(adapter_id)
    if not ad:
        raise HTTPException(status_code=404, detail=f"Adapter {adapter_id} not found")
    h = await ad.health()
    cfg = ad.config
    return {
        "adapter_id": cfg.adapter_id,
        "protocol": cfg.protocol.value if hasattr(cfg.protocol, "value") else str(cfg.protocol),
        "station_id": cfg.station_id,
        "enabled": cfg.enabled,
        "poll_interval_ms": cfg.poll_interval_ms,
        "tags": [{"source_tag": t.source_tag, "metric": t.metric, "unit": t.unit, "scale": t.scale, "offset": t.offset, "data_type": t.data_type, "compound_formula": t.compound_formula, "source_tags": t.source_tags} for t in cfg.tags],
        "params": cfg.params,
        "health": {"status": h.status, "last_ok_ts": h.last_ok_ts, "last_error": h.last_error, "message_count": h.message_count, "error_count": h.error_count},
    }


@app.delete("/adapters/{adapter_id}", tags=["adapters"])
async def delete_adapter(adapter_id: str, claims: dict = Depends(require_auth)):
    ok = await _registry_global.remove(adapter_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Adapter {adapter_id} not found")
    return {"deleted": adapter_id}


@app.post("/adapters/{adapter_id}/start", tags=["adapters"])
async def start_adapter(adapter_id: str, claims: dict = Depends(require_auth)):
    ad = await _registry_global.get(adapter_id)
    if not ad:
        raise HTTPException(status_code=404, detail=f"Adapter {adapter_id} not found")
    await ad.start()
    return {"adapter_id": adapter_id, "status": (await ad.health()).status}


@app.post("/adapters/{adapter_id}/stop", tags=["adapters"])
async def stop_adapter(adapter_id: str, claims: dict = Depends(require_auth)):
    ad = await _registry_global.get(adapter_id)
    if not ad:
        raise HTTPException(status_code=404, detail=f"Adapter {adapter_id} not found")
    await ad.stop()
    return {"adapter_id": adapter_id, "status": (await ad.health()).status}


@app.post("/adapters/{adapter_id}/poll", tags=["adapters"], summary="Poll once and return normalized readings")
async def poll_adapter(adapter_id: str, claims: dict = Depends(optional_auth)):
    ad = await _registry_global.get(adapter_id)
    if not ad:
        raise HTTPException(status_code=404, detail=f"Adapter {adapter_id} not found")
    try:
        readings = await ad.poll_once()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Poll failed: {e}") from e
    # also publish via pipeline path
    if _pipeline:
        for r in readings:
            await _pipeline.process_one(r)
    return [_reading_to_out(r) for r in readings]


# ---------------------------------------------------------------------------
# readings / events
# ---------------------------------------------------------------------------
@app.get("/readings", tags=["telemetry"], summary="Poll all adapters once")
async def readings_all(claims: dict = Depends(optional_auth)):
    all_readings: List[Dict[str, Any]] = []
    for ad in _registry_global.all_adapters():
        try:
            rs = await ad.poll_once()
            for r in rs:
                if _pipeline:
                    await _pipeline.process_one(r)
                all_readings.append(_reading_to_out(r))
        except Exception as e:
            logger.warning("poll failed", adapter_id=ad.adapter_id, error=str(e))
    return all_readings


@app.post("/ingest", tags=["telemetry"], summary="Direct ingest of a normalized reading (for gateways)")
async def ingest_reading(body: IngestReadingIn, claims: dict = Depends(optional_auth)):
    r = NormalizedReading(
        station_id=body.station_id,
        metric=body.metric,
        value=body.value,
        unit=body.unit,
        timestamp=time.time(),
        quality=Quality.GOOD,
        protocol=body.protocol,
        adapter_id=body.adapter_id or "gateway",
        source_tag=body.source_tag,
    )
    if _pipeline:
        await _pipeline.process_one(r)
    else:
        await _publisher_global.publish_reading(r)
    ev = detect_defect(r)
    if ev:
        return {"reading": _reading_to_out(r), "defect": {"station_id": ev.station_id, "track": ev.track.value, "defect_class": ev.defect_class.value, "confidence": ev.confidence, "protocol": ev.protocol}}
    return {"reading": _reading_to_out(r), "defect": None}


@app.get("/events", tags=["telemetry"], summary="Synthetic derived DefectEvents (demo)")
async def list_events(limit: int = Query(default=5, ge=1, le=100)):
    from ..domain.events import make_event, DefectClass

    protos = ["opcua", "modbus", "mqtt", "mtconnect", "ethernet_ip", "camera"]
    out = []
    for i in range(limit):
        ev = make_event(proto=protos[i % len(protos)])
        out.append({"station_id": ev.station_id, "track": ev.track.value, "defect_class": ev.defect_class.value, "confidence": ev.confidence, "latency_ms": ev.latency_ms, "timestamp": ev.timestamp, "protocol": ev.protocol, "adapter_id": ev.adapter_id})
    return out


# ---------------------------------------------------------------------------
# tag-map compounding preview (pure, no I/O) — useful for UI
# ---------------------------------------------------------------------------
class CompoundPreviewIn(BaseModel):
    formula: str
    variables: Dict[str, float]


@app.post("/tag-map/preview", tags=["adapters"], summary="Preview tag-map compound formula")
async def tag_map_preview(body: CompoundPreviewIn):
    from ..domain.tag_map import evaluate_compound_formula

    try:
        value = evaluate_compound_formula(body.formula, body.variables)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"formula": body.formula, "variables": body.variables, "value": value}


# ---------------------------------------------------------------------------
# OpenAPI export helper (used by tests / README)
# ---------------------------------------------------------------------------
@app.get("/openapi.json", include_in_schema=False)
async def openapi_json():
    return app.openapi()

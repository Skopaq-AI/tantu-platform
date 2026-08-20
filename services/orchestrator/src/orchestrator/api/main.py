"""Orchestrator FastAPI app — ingest, reports, window, health + NATS subscriber."""
from __future__ import annotations

import time
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional, List, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..infra.config import settings
from ..infra.db import init_db, close_db
from ..infra.nats_bus import nats_bus
from ..infra.reasoning_client import reasoning_client
from ..infra.persistence import list_reports, get_report
from ..application.policy import get_policy
from ..application.orchestrator_service import OrchestratorService
from ..domain.events import DefectEvent, DefectClass, Track

log = logging.getLogger("orchestrator.api")

# Global policy + service — shared
_policy = get_policy()
_service = OrchestratorService(policy=_policy)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Try NATS connect + subscribe (non-blocking, best-effort)
    try:
        await nats_bus.subscribe(_service.ingest, subjects=settings.nats_subjects_list)
    except Exception as e:
        log.warning("orchestrator NATS subscribe on startup failed: %s", e)
    log.info(
        "orchestrator startup: port %s threshold=%.2f window=%d ttl=%.0fs NATS=%s reasoning=%s",
        settings.port,
        settings.confidence_threshold,
        settings.window_size,
        settings.window_ttl_s,
        settings.nats_url,
        settings.reasoning_copilot_url,
    )
    yield
    await nats_bus.close()
    await reasoning_client.close()
    await close_db()


app = FastAPI(
    title="TANTU Orchestrator",
    version="0.1.0",
    description=(
        "Event window orchestration — escalates when (fault_count >=2) OR any confidence ≥ threshold (default 0.97). "
        "NATS subscriber on tantu.events.derived.>, calls reasoning-copilot, persists CorrelationReport to TimescaleDB, idempotent."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic ingress ───────────────────────────────────────────────

class IngestRequest(BaseModel):
    station_id: str = Field(..., example="line2-cluster1-gauge3")
    defect_class: str = Field("none", example="pressure_drift")
    confidence: float = Field(0.95, ge=0, le=1)
    protocol: str = Field("opcua")
    plant_id: str = Field("plant-demo-01")
    event_id: Optional[str] = None
    track: str = Field("line")
    latency_ms: float = Field(22.0)
    adapter_id: str = Field("")


class IngestResponse(BaseModel):
    event_id: str
    escalated: bool
    report: Optional[dict] = None
    window_size: int = 0


# ── Health ─────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health():
    return {
        "status": "ok",
        "service": "orchestrator",
        "ts": time.time(),
        "frames_never_leave": True,
        "policy": {
            "confidence_threshold": settings.confidence_threshold,
            "window_size": settings.window_size,
            "window_ttl_s": settings.window_ttl_s,
        },
        "windows": _service.window_snapshot(),
        "reports_cached": len(_service.reports_memory()),
    }


@app.get("/ready", tags=["ops"])
async def ready():
    # DB probe
    db_status = "unknown"
    try:
        from sqlalchemy import text as _text
        from ..infra.db import get_engine
        eng = get_engine()
        async with eng.connect() as conn:
            await conn.execute(_text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"degraded: {e}"[:300]
    nats_status = "ok" if nats_bus._nc is not None else "degraded: not connected (will retry)"
    is_ready = True  # orchestrator is usable even without DB/NATS (memory fallback)
    return {"ready": is_ready, "db": db_status, "nats": nats_status, "ts": time.time()}


@app.get("/window", tags=["debug"])
async def get_window():
    return {"windows": _service.window_snapshot(), "ts": time.time()}


# ── Ingest (HTTP ingress mirrors NATS path, shares idempotency) ─────

def _to_domain(body: IngestRequest) -> DefectEvent:
    try:
        klass = DefectClass(body.defect_class)
    except ValueError:
        klass = DefectClass.NONE
    try:
        track = Track(body.track)
    except ValueError:
        track = Track.LINE
    return DefectEvent(
        station_id=body.station_id,
        track=track,
        defect_class=klass,
        confidence=body.confidence,
        latency_ms=body.latency_ms,
        protocol=body.protocol,
        plant_id=body.plant_id,
        event_id=body.event_id or uuid.uuid4().hex,
        adapter_id=body.adapter_id,
    )


@app.post("/ingest", response_model=IngestResponse, tags=["ingest"])
async def ingest(body: IngestRequest):
    ev = _to_domain(body)
    escalated, report = await _service.ingest(ev)
    size = _service.window_snapshot().get(ev.plant_id, 0)
    return IngestResponse(
        event_id=ev.event_id,
        escalated=escalated,
        report=report.to_dict() if report else None,
        window_size=size,
    )


@app.post("/ingest/batch", tags=["ingest"])
async def ingest_batch(bodies: List[IngestRequest]):
    results = []
    for b in bodies:
        ev = _to_domain(b)
        escalated, report = await _service.ingest(ev)
        results.append({"event_id": ev.event_id, "escalated": escalated, "report": report.to_dict() if report else None})
    return {"results": results}


# ── Reports ─────────────────────────────────────────────────────────

@app.get("/reports", tags=["reports"])
async def reports(limit: int = 20, plant_id: Optional[str] = None):
    # Try DB first, fallback to memory
    db_reports = await list_reports(limit=limit, plant_id=plant_id)
    if db_reports:
        return {"reports": [r.to_dict() for r in db_reports], "source": "db"}
    mem = _service.reports_memory()
    if plant_id:
        mem = [r for r in mem if r.plant_id == plant_id]
    mem = sorted(mem, key=lambda r: r.created_at, reverse=True)[:limit]
    return {"reports": [r.to_dict() for r in mem], "source": "memory"}


@app.get("/reports/{report_id}", tags=["reports"])
async def report_by_id(report_id: str):
    r = await get_report(report_id)
    if r:
        return r.to_dict()
    # memory fallback
    for m in _service.reports_memory():
        if m.id == report_id:
            return m.to_dict()
    raise HTTPException(status_code=404, detail="report not found")


# ── Debug: clear state ──────────────────────────────────────────────

@app.post("/debug/clear", tags=["debug"], include_in_schema=False)
async def debug_clear():
    _service.clear()
    return {"cleared": True, "ts": time.time()}

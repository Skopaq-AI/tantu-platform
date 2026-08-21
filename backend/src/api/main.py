from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time
import uuid
import logging

from ..domain.events import DefectEvent, DefectClass, Track, make_event
from ..application.orchestrator import Orchestrator
from ..adapters.reasoning_stub import DualStub
from ..infra.security import verify_jwt, authorize, rate_limit, has_permission, async_rate_limit, audit_log
from .auth import router as auth_router

log = logging.getLogger("tantu.api")

app = FastAPI(title="TANTU API", version="0.1.0", description="Mixed-fleet intelligence — derived events only")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Include auth + users routes (public + protected)
app.include_router(auth_router)

orch = Orchestrator(DualStub())

class IngestIn(BaseModel):
    station_id: str
    defect_class: str = "none"
    confidence: float = 0.9
    protocol: str = "opcua"
    plant_id: Optional[str] = None  # optional ABAC plant context
    org_id: Optional[str] = None

class AskIn(BaseModel):
    question: str
    plant_id: str = "plant-demo-01"
    air_gapped: bool = False

class AckIn(BaseModel):
    event_id: Optional[str] = None
    station_id: Optional[str] = None
    plant_id: Optional[str] = None
    comment: Optional[str] = None

@app.get("/health")
async def health(): return {"status": "ok", "ts": time.time(), "frames_never_leave": True}

@app.get("/info")
async def info(): return {"name": "TANTU", "codename_note": "uncleared — externals use Skopaq AI", "dual_reasoning": "nemotron-9b on-prem + gemini-er2 cloud on derived events only"}

# ── Protected endpoints ──────────────────────────────────────────────────

@app.post("/ingest")
async def ingest(body: IngestIn, request: Request, claims: Dict[str, Any] = Depends(verify_jwt)):
    # Rate limit per sub / station
    key = f"ingest:{claims.get('sub')}:{body.station_id}"
    # sync fallback
    if not rate_limit(key, max_hits=30, window_s=60):
        raise HTTPException(status_code=429, detail="rate limited")
    allowed = await async_rate_limit(key, max_hits=30, window_s=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="rate limited")

    # RBAC permission
    if not has_permission(claims, "ingest:write") and not has_permission(claims, "ingest:post"):
        if not has_permission(claims, "*"):
            raise HTTPException(status_code=403, detail="missing permission ingest:write")

    # ABAC plant check: if body plant_id provided, must be in scope; else try station mapping? just check first plant
    target_plant = body.plant_id or claims.get("plant_id")
    if target_plant and not authorize(claims, plant_id=target_plant):
        raise HTTPException(status_code=403, detail=f"ABAC plant deny: {target_plant}")

    # Org isolation: if org_id provided must match
    if body.org_id and body.org_id != claims.get("org_id"):
        # allow super admin cross-org?
        if not authorize(claims, org_id=body.org_id):
            raise HTTPException(status_code=403, detail="org isolation deny")

    klass = DefectClass(body.defect_class) if body.defect_class in DefectClass._value2member_map_ else DefectClass.NONE
    ev = DefectEvent(station_id=body.station_id, track=Track.LINE, defect_class=klass, confidence=body.confidence, latency_ms=22.5, protocol=body.protocol)
    orch.ingest(ev)
    report = await orch.maybe_escalate()

    audit_log("ingest", claims, request=request, plant_id=target_plant)
    return {"event": ev, "escalated": report is not None, "report": report}

@app.post("/ask")
async def ask(body: AskIn, request: Request, claims: Dict[str, Any] = Depends(verify_jwt)):
    key = f"ask:{claims.get('sub')}"
    if not rate_limit(key, max_hits=30, window_s=60):
        raise HTTPException(status_code=429, detail="rate limited")
    allowed = await async_rate_limit(key, max_hits=30, window_s=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="rate limited")

    if not has_permission(claims, "ask:execute") and not has_permission(claims, "reasoning:read") and not has_permission(claims, "ask:read"):
        if not has_permission(claims, "*"):
            raise HTTPException(status_code=403, detail="missing permission ask:execute")

    if not authorize(claims, plant_id=body.plant_id):
        raise HTTPException(status_code=403, detail=f"ABAC plant deny: {body.plant_id}")

    stub = DualStub()
    answer = await stub.answer(body.question, {"plant_id": body.plant_id, "air_gapped": body.air_gapped})
    vernacular = {"hi": "Line 2 pressure jaasti — valve 3 check karo", "ta": "Line 2 pressure jaasti — valve 3 paarunga"}

    audit_log("ask", claims, request=request, plant_id=body.plant_id)
    return {"answer": answer, "vernacular": vernacular, "grounded": True, "air_gapped_routed_to": "on-prem SLM" if body.air_gapped else "gemini-er2"}

@app.get("/events")
async def list_events(request: Request, limit: int = 10, plant_id: Optional[str] = Query(None), claims: Dict[str, Any] = Depends(verify_jwt)):
    key = f"events:{claims.get('sub')}"
    if not rate_limit(key, max_hits=60, window_s=60):
        raise HTTPException(status_code=429, detail="rate limited")
    allowed = await async_rate_limit(key, max_hits=60, window_s=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="rate limited")

    if not has_permission(claims, "events:read") and not has_permission(claims, "telemetry:read"):
        if not has_permission(claims, "*"):
            raise HTTPException(status_code=403, detail="missing permission events:read")

    # ABAC: if plant_id query provided, must be in scope
    if plant_id and not authorize(claims, plant_id=plant_id):
        raise HTTPException(status_code=403, detail=f"ABAC plant deny: {plant_id}")

    # demo: generate synthetic derived events
    events = [make_event(proto=p) for p in ["opcua","modbus","camera"][:limit]]
    audit_log("list_events", claims, request=request, plant_id=plant_id)
    return events

@app.get("/poll")
async def poll(request: Request, limit: int = 10, plant_id: Optional[str] = Query(None), claims: Dict[str, Any] = Depends(verify_jwt)):
    key = f"poll:{claims.get('sub')}"
    if not rate_limit(key, max_hits=60, window_s=60):
        raise HTTPException(status_code=429, detail="rate limited")
    allowed = await async_rate_limit(key, max_hits=60, window_s=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="rate limited")

    if not has_permission(claims, "poll:read") and not has_permission(claims, "events:read"):
        if not has_permission(claims, "*"):
            raise HTTPException(status_code=403, detail="missing permission poll:read")

    if plant_id and not authorize(claims, plant_id=plant_id):
        raise HTTPException(status_code=403, detail=f"ABAC plant deny: {plant_id}")

    # Reuse orchestrator window as poll source? Return pending correlations
    # For demo, return derived events with polling metadata
    events = [make_event(proto=p) for p in ["opcua","modbus","camera"][:limit]]
    audit_log("poll", claims, request=request, plant_id=plant_id)
    return {"events": events, "pending": len(orch.window), "plant_id": plant_id or claims.get("plant_ids", ["plant-demo-01"])[0]}

@app.post("/ack")
async def ack(body: AckIn, request: Request, claims: Dict[str, Any] = Depends(verify_jwt)):
    key = f"ack:{claims.get('sub')}"
    if not rate_limit(key, max_hits=30, window_s=60):
        raise HTTPException(status_code=429, detail="rate limited")
    allowed = await async_rate_limit(key, max_hits=30, window_s=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="rate limited")

    if not has_permission(claims, "ack:write") and not has_permission(claims, "maintenance:write"):
        if not has_permission(claims, "*"):
            raise HTTPException(status_code=403, detail="missing permission ack:write")

    target_plant = body.plant_id
    if target_plant and not authorize(claims, plant_id=target_plant):
        raise HTTPException(status_code=403, detail=f"ABAC plant deny: {target_plant}")

    # stub ack: clear window if acked
    if body.event_id or body.station_id:
        # pretend acknowledged
        pass
    audit_log("ack", claims, request=request, plant_id=target_plant)
    return {"acked": True, "event_id": body.event_id or body.station_id or str(uuid.uuid4()), "by": claims.get("sub"), "ts": time.time()}

@app.get("/metrics")
async def metrics(request: Request, claims: Dict[str, Any] = Depends(verify_jwt)):
    key = f"metrics:{claims.get('sub')}"
    if not rate_limit(key, max_hits=30, window_s=60):
        raise HTTPException(status_code=429, detail="rate limited")
    allowed = await async_rate_limit(key, max_hits=60, window_s=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="rate limited")

    if not has_permission(claims, "metrics:read") and not has_permission(claims, "health:read"):
        if not has_permission(claims, "*"):
            raise HTTPException(status_code=403, detail="missing permission metrics:read")

    audit_log("metrics", claims, request=request)
    return {
        "uptime_s": time.time() - (getattr(metrics, "_start", time.time())),
        "events_window": len(orch.window),
        "org_id": claims.get("org_id"),
        "plant_ids": claims.get("plant_ids"),
        "ts": time.time(),
    }
# Store start for metrics uptime
metrics._start = time.time()

# ── Additional alias routes for frontend compat ──────────────────────────
@app.get("/api/metrics", include_in_schema=False)
async def api_metrics(request: Request, claims: Dict[str, Any] = Depends(verify_jwt)):
    return await metrics(request, claims)

@app.get("/api/events", include_in_schema=False)
async def api_events(request: Request, limit: int = 10, plant_id: Optional[str] = Query(None), claims: Dict[str, Any] = Depends(verify_jwt)):
    return await list_events(request, limit, plant_id, claims)

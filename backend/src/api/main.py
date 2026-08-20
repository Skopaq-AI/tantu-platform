from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time

from ..domain.events import DefectEvent, DefectClass, Track, make_event
from ..application.orchestrator import Orchestrator
from ..adapters.reasoning_stub import DualStub
from ..infra.security import verify_jwt, authorize, rate_limit

app = FastAPI(title="TANTU API", version="0.1.0", description="Mixed-fleet intelligence — derived events only")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

orch = Orchestrator(DualStub())

class IngestIn(BaseModel):
    station_id: str
    defect_class: str = "none"
    confidence: float = 0.9
    protocol: str = "opcua"

class AskIn(BaseModel):
    question: str
    plant_id: str = "plant-demo-01"
    air_gapped: bool = False

@app.get("/health")
async def health(): return {"status": "ok", "ts": time.time(), "frames_never_leave": True}

@app.get("/info")
async def info(): return {"name": "TANTU", "codename_note": "uncleared — externals use Skopaq AI", "dual_reasoning": "nemotron-9b on-prem + gemini-er2 cloud on derived events only"}

@app.post("/ingest")
async def ingest(body: IngestIn, authorization: Optional[str] = Header(None)):
    # stub auth — in prod verify_jwt
    if not rate_limit(body.station_id): raise HTTPException(429, "rate limited")
    klass = DefectClass(body.defect_class) if body.defect_class in DefectClass._value2member_map_ else DefectClass.NONE
    ev = DefectEvent(station_id=body.station_id, track=Track.LINE, defect_class=klass, confidence=body.confidence, latency_ms=22.5, protocol=body.protocol)
    orch.ingest(ev)
    report = await orch.maybe_escalate()
    return {"event": ev, "escalated": report is not None, "report": report}

@app.post("/ask")
async def ask(body: AskIn):
    # GENAI — grounded via RAG stub
    stub = DualStub()
    answer = await stub.answer(body.question, {"plant_id": body.plant_id, "air_gapped": body.air_gapped})
    # vernacular stub
    vernacular = {"hi": "Line 2 pressure jaasti — valve 3 check karo", "ta": "Line 2 pressure jaasti — valve 3 paarunga"}
    return {"answer": answer, "vernacular": vernacular, "grounded": True, "air_gapped_routed_to": "on-prem SLM" if body.air_gapped else "gemini-er2"}

@app.get("/events")
async def list_events(limit: int = 10):
    # demo: generate synthetic derived events
    return [make_event(proto=p) for p in ["opcua","modbus","camera"][:limit]]

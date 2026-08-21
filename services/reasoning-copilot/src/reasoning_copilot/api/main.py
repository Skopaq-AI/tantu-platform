"""FastAPI — reasoning-copilot on :8003.

Endpoints:
  GET  /health
  GET  /info
  POST /ask
  POST /correlate
  POST /rag/ingest
  POST /rag/search
  GET  /rag/stats
  POST /vernacular/tts
  POST /vernacular/stt
  GET  /prompts
  POST /auth/token  (dev helper)

Guards: JWT optional (enforced when header present), rate limit, grounded RAG,
hallucination guard, token costing $2/M in $10/M out, OpenTelemetry.
"""

from __future__ import annotations

import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from .models import (
    AskIn,
    AskOut,
    CorrelateIn,
    CorrelateOut,
    RagIngestIn,
    RagSearchIn,
    TtsIn,
    SttIn,
)
from .security import optional_auth, issue_jwt
from .ratelimit import check_rate_limit
from .telemetry import init_telemetry
from ..rag import RagStore, Document, format_context, build_citations
from ..planner import DualRouter
from ..vernacular import to_vernacular, TtsSttService, SUPPORTED_LANGS
from ..planner.prompts import PROMPT_REGISTRY, list_prompts

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

# Singletons — initialized on startup
rag_store: RagStore | None = None
router: DualRouter | None = None
tts_stt: TtsSttService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_store, router, tts_stt
    rag_store = RagStore()
    router = DualRouter()
    tts_stt = TtsSttService()
    # seed runbooks if empty
    if rag_store.count() == 0:
        from ..rag.store import Document as Doc

        seeds = [
            Doc(
                id="runbook-press-01",
                text="Line 2 pressure high (>8 bar): check valve 3, inspect regulator, relieve accumulator. Max safe 8 bar per tag map press_line2.",
                metadata={"plant_id": "plant-demo-01", "type": "runbook", "station": "line2"},
            ),
            Doc(
                id="runbook-vib-01",
                text="Vibration RMS >4.5 mm/s at Line 2 cluster indicates bearing wear. Check bearing temp, schedule replacement. Tag: vib_line2_rms.",
                metadata={"plant_id": "plant-demo-01", "type": "runbook", "station": "line2"},
            ),
            Doc(
                id="tagmap-line2-01",
                text="Tag map Line 2: press_line2 (0-10 bar, OPC-UA ns=2;i=1001), vib_line2_rms (0-20 mm/s, Modbus 40001), bearing_temp_c (0-150 C).",
                metadata={"plant_id": "plant-demo-01", "type": "tag_map"},
            ),
            Doc(
                id="runbook-thermal-01",
                text="Thermal high >80C at chamber: check cooling fan, verify coolant flow 2.1 L/min. Do not exceed 85C.",
                metadata={"plant_id": "plant-demo-01", "type": "runbook"},
            ),
            Doc(
                id="runbook-solder-01",
                text="Solder void defect: check reflow profile peak 240C, 60-90s above liquidus. Inspect stencil aperture.",
                metadata={"plant_id": "plant-demo-01", "type": "runbook"},
            ),
        ]
        rag_store.add_many(seeds)
        log.info("Seeded %s docs, backend=%s", rag_store.count(), rag_store.backend)
    log.info(
        "Reasoning Copilot ready — port %s qdrant=%s gemini=%s",
        settings.port,
        rag_store.backend,
        bool(settings.gemini_api_key),
    )
    yield


app = FastAPI(
    title="TANTU Reasoning Copilot",
    version=settings.service_version,
    description="Dual-sourced GENAI (Gemini ER2 + Nemotron-9B) · RAG Qdrant · vernacular hi/ta/te/kn",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_telemetry(app)

# ---- helpers ---------------------------------------------------------------


def get_store() -> RagStore:
    assert rag_store is not None
    return rag_store


def get_router() -> DualRouter:
    assert router is not None
    return router


def get_tts() -> TtsSttService:
    assert tts_stt is not None
    return tts_stt


@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.time() - start) * 1000:.1f}ms"
    return response


# ---- health / info --------------------------------------------------------


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.service_version,
        "ts": time.time(),
        "qdrant_backend": (rag_store.backend if rag_store else "init"),
        "rag_docs": (rag_store.count() if rag_store else 0),
        "frames_never_leave": True,
    }


@app.get("/info")
async def info():
    return {
        "name": "TANTU Reasoning Copilot",
        "codename_note": "externals use Skopaq AI",
        "version": settings.service_version,
        "port": settings.port,
        "dual_reasoning": "nemotron-9b on-prem (vLLM/Ollama) + gemini-er2 cloud (google-genai SDK)",
        "rag": "qdrant-client + sentence-transformers (hash fallback) cosine search, chunking, citations",
        "vernacular": SUPPORTED_LANGS,
        "costing": {"in_per_m": settings.gemini_in_per_m, "out_per_m": settings.gemini_out_per_m},
        "prompts": list_prompts(),
    }


@app.get("/prompts")
async def prompts():
    return {
        k: {
            "version": v.version,
            "description": v.description,
            "grounded": v.grounded,
            "require_citations": v.require_citations,
        }
        for k, v in PROMPT_REGISTRY.items()
    }


# ---- auth helper (dev) -----------------------------------------------------


@app.post("/auth/token")
async def auth_token(
    sub: str = "operator-01", plant_id: str = "plant-demo-01", role: str = "operator"
):
    tok = issue_jwt(sub, plant_id, role)
    return {"access_token": tok, "token_type": "bearer", "plant_id": plant_id, "role": role}


# ---- RAG -------------------------------------------------------------------


@app.post("/rag/ingest")
async def rag_ingest(body: RagIngestIn, request: Request, claims=Depends(optional_auth)):
    check_rate_limit(request)
    store = get_store()
    doc = Document(id=body.id, text=body.text, metadata=body.metadata)
    n = store.add(doc)
    return {
        "ingested": body.id,
        "chunks": n,
        "total_points": store.count(),
        "backend": store.backend,
    }


@app.post("/rag/search")
async def rag_search(body: RagSearchIn, request: Request, claims=Depends(optional_auth)):
    check_rate_limit(request)
    store = get_store()
    hits = store.search(body.query, top_k=body.top_k)
    return {
        "query": body.query,
        "hits": [
            {
                "doc_id": h.doc_id,
                "text": h.text[:400],
                "score": round(h.score, 4),
                "metadata": h.metadata,
            }
            for h in hits
        ],
        "context": format_context(hits),
        "backend": store.backend,
    }


@app.get("/rag/stats")
async def rag_stats(claims=Depends(optional_auth)):
    store = get_store()
    return {
        "collection": store.collection,
        "count": store.count(),
        "backend": store.backend,
        "embedding_model": store.embedder.model_name,
        "dim": store.embedder.dim,
        "is_transformer": store.embedder.is_transformer,
    }


# ---- vernacular ------------------------------------------------------------


@app.post("/vernacular/tts")
async def vernacular_tts(body: TtsIn, request: Request, claims=Depends(optional_auth)):
    check_rate_limit(request)
    svc = get_tts()
    res = await svc.synthesize(body.text, body.lang.value)
    return res


@app.post("/vernacular/stt")
async def vernacular_stt(body: SttIn, request: Request, claims=Depends(optional_auth)):
    check_rate_limit(request)
    svc = get_tts()
    res = await svc.transcribe(body.audio_base64, body.lang.value)
    return res


# ---- ask -------------------------------------------------------------------


@app.post("/ask", response_model=AskOut)
async def ask(body: AskIn, request: Request, claims=Depends(optional_auth)):
    check_rate_limit(request)
    t0 = time.time()
    store = get_store()
    rt = get_router()

    # plant scoping: if claims present, enforce ABAC
    if claims and claims.get("plant_id") and claims["plant_id"] != body.plant_id:
        # allow but warn? strict: mismatch -> 403 if role not plant_admin
        if claims.get("role") != "plant_admin":
            raise HTTPException(
                status_code=403,
                detail=f"plant_id mismatch: token {claims['plant_id']} vs request {body.plant_id}",
            )

    hits = store.search(body.question, top_k=body.top_k)
    rag_context = format_context(hits)
    rag_doc_ids = [h.doc_id for h in hits]

    # prompt version override: map ask_v2 etc via prompt_name
    prompt_name = body.prompt_version if body.prompt_version in PROMPT_REGISTRY else "ask_v1"

    # call router directly with prompt_name if not ask_v1
    if prompt_name != "ask_v1":
        variables = {
            "question": body.question,
            "plant_id": body.plant_id,
            "rag_context": rag_context,
            "lang": body.lang.value,
            "top_k": body.top_k,
        }
        raw = await rt._route_generate(
            prompt_name, variables, rag_doc_ids, air_gapped=body.air_gapped
        )
        text = raw["text"]
        backend = raw["backend"]
        model = raw["model"]
        tokens_in = raw["tokens_in"]
        tokens_out = raw["tokens_out"]
        cost = raw["cost_usd"]
    else:
        raw = await rt.answer(
            body.question,
            rag_context,
            rag_doc_ids,
            plant_id=body.plant_id,
            lang=body.lang.value,
            air_gapped=body.air_gapped,
            top_k=body.top_k,
        )
        text = raw["text"]
        backend = raw["backend"]
        model = raw["model"]
        tokens_in = raw["tokens_in"]
        tokens_out = raw["tokens_out"]
        cost = raw["cost_usd"]

    vernacular_text = to_vernacular(text, body.lang.value)
    citations = build_citations(hits)

    latency_ms = (time.time() - t0) * 1000
    return AskOut(
        answer=text,
        vernacular=vernacular_text,
        lang=body.lang,
        citations=citations,
        grounded=len(citations) > 0 or "needs human check" in text.lower(),
        backend=backend,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost,
        latency_ms=round(latency_ms, 1),
        air_gapped=body.air_gapped,
        prompt_version=prompt_name,
    )


# ---- correlate -------------------------------------------------------------


@app.post("/correlate", response_model=CorrelateOut)
async def correlate(body: CorrelateIn, request: Request, claims=Depends(optional_auth)):
    check_rate_limit(request)
    t0 = time.time()
    store = get_store()
    rt = get_router()

    if claims and claims.get("plant_id") and claims["plant_id"] != body.plant_id:
        if claims.get("role") != "plant_admin":
            raise HTTPException(status_code=403, detail="plant_id mismatch")

    # Build RAG query from events
    defect_tokens = " ".join(
        [e.defect_class.value for e in body.events if e.defect_class.value != "none"]
    )
    stations = " ".join([e.station_id for e in body.events])
    rag_query = (
        f"{defect_tokens} {stations} {body.plant_id}".strip() or "pressure vibration thermal"
    )
    hits = store.search(rag_query, top_k=body.top_k)
    rag_context = format_context(hits)
    rag_doc_ids = [h.doc_id for h in hits]

    prompt_name = body.prompt_version if body.prompt_version in PROMPT_REGISTRY else "correlate_v1"

    events_for_llm = [e.model_dump() for e in body.events]
    if prompt_name != "correlate_v1":
        import json as _json

        variables = {
            "events_json": _json.dumps(events_for_llm, default=str),
            "rag_context": rag_context,
            "lang": body.lang.value,
            "top_k": body.top_k,
        }
        raw = await rt._route_generate(
            prompt_name, variables, rag_doc_ids, air_gapped=body.air_gapped
        )
    else:
        raw = await rt.correlate(
            events_for_llm,
            rag_context,
            rag_doc_ids,
            lang=body.lang.value,
            air_gapped=body.air_gapped,
            top_k=body.top_k,
        )

    summary = raw["text"]
    summary_vern = to_vernacular(summary, body.lang.value)
    citations = build_citations(hits)

    # derive contributing + confidence
    contributing = sorted({e.station_id for e in body.events})
    # confidence: boost if grounded
    confidence = 0.82 if citations else 0.62
    if "needs human check" in summary.lower():
        confidence = min(confidence, 0.55)

    latency_ms = (time.time() - t0) * 1000
    return CorrelateOut(
        summary=summary,
        summary_vernacular=summary_vern,
        contributing=contributing,
        confidence=round(confidence, 2),
        citations=citations,
        grounded=len(citations) > 0,
        backend=raw["backend"],
        model=raw["model"],
        tokens_in=raw["tokens_in"],
        tokens_out=raw["tokens_out"],
        cost_usd=raw["cost_usd"],
        latency_ms=round(latency_ms, 1),
        air_gapped=body.air_gapped,
        prompt_version=prompt_name,
    )

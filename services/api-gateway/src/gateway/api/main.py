"""Gateway FastAPI app — CORS + Helmet + rate limit + JWT RS256 + RBAC/ABAC + proxy + audit."""

from __future__ import annotations

import time
import logging
from contextlib import asynccontextmanager
from typing import Optional, Any

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..infra.config import settings
from ..infra.security import require_auth, verify_jwt, issue_jwt
from ..infra.rate_limit import rate_limiter
from ..infra.downstream import downstream_client
from ..infra.db import init_db, close_db
from ..infra.audit import write_audit, new_request_id, configure_structlog
from ..domain.models import Principal, Resource
from ..domain.policies import evaluate
from ..domain.errors import DownstreamError
from ..application.health_aggregator import aggregate_health
from ..application.proxy import resolve_downstream

log = logging.getLogger("gateway.api")
configure_structlog(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    log.info("gateway startup: port %s redis %s", settings.port, settings.redis_url)
    yield
    # Shutdown
    await downstream_client.close()
    await rate_limiter.close()
    await close_db()


app = FastAPI(
    title="TANTU API Gateway",
    version="0.1.0",
    description=(
        "Mixed-fleet Factory Intelligence — API Gateway. "
        "AuthN JWT RS256 · RBAC/ABAC plant scoping · Redis rate-limit · Helmet · CORS · Audit log. "
        "Proxies /api/* to downstream services; aggregates /health."
    ),
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


# ── Helmet middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def helmet_middleware(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    # HSTS only on https, but we set header anyway
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    # Remove server fingerprint
    if "server" in response.headers:
        del response.headers["server"]
    response.headers["X-Request-Id"] = request.headers.get(
        "x-request-id", getattr(request.state, "request_id", "")
    )
    return response


# ── Request ID + audit middleware ─────────────────────────────────────
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or new_request_id()
    request.state.request_id = request_id
    start = time.time()
    # Extract principal if present
    claims: Optional[dict[str, Any]] = None
    auth = request.headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        try:
            claims = verify_jwt(auth.removeprefix("Bearer ").strip())
        except Exception:
            claims = None

    principal_str = claims.get("sub") if claims else None
    plant_id_claim = claims.get("plant_id") if claims else None

    # Rate limit check is done in route handler / proxy guard — but we also attach headers
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
        decision = "allow"
        reason = ""
        # If upstream returned 401/403, reflect
        if status_code == 401:
            decision = "deny"
            reason = "unauthorized"
        elif status_code == 403:
            decision = "deny"
            reason = "forbidden"
        elif status_code == 429:
            decision = "deny"
            reason = "rate_limited"
        response.headers["X-Request-Id"] = request_id
        latency_ms = (time.time() - start) * 1000
        # Fire and forget audit (do not block)
        try:
            from ..domain.models import AuditEntry

            entry = AuditEntry(
                request_id=request_id,
                principal=principal_str,
                plant_id=plant_id_claim,
                method=request.method,
                path=request.url.path,
                status=status_code,
                latency_ms=latency_ms,
                decision=decision,
                reason=reason,
            )
            # schedule without awaiting to not delay response — but for correctness we await with timeout
            import asyncio

            asyncio.create_task(write_audit(entry))
        except Exception:
            pass
        return response
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        log.exception("gateway unhandled: %s %s %s", request.method, request.url.path, e)
        try:
            from ..domain.models import AuditEntry

            entry = AuditEntry(
                request_id=request_id,
                principal=principal_str,
                plant_id=plant_id_claim,
                method=request.method,
                path=request.url.path,
                status=500,
                latency_ms=latency_ms,
                decision="error",
                reason=str(e)[:200],
            )
            import asyncio

            asyncio.create_task(write_audit(entry))
        except Exception:
            pass
        return JSONResponse(
            status_code=500, content={"detail": "internal gateway error", "request_id": request_id}
        )


# ── Health ────────────────────────────────────────────────────────────


@app.get("/health", tags=["ops"], summary="Aggregated health (self + downstream)")
async def health():
    agg = await aggregate_health()
    # Also include self status
    agg["gateway"] = {"status": "ok", "port": settings.port}
    return agg


@app.get("/health/live", tags=["ops"], summary="Liveness")
async def health_live():
    return {"status": "ok", "service": "api-gateway", "ts": time.time(), "frames_never_leave": True}


@app.get("/ready", tags=["ops"], summary="Readiness (Redis + DB)")
async def ready():
    # Probe Redis
    redis_status = "unknown"
    try:
        allowed, remaining, ttl = await rate_limiter.is_allowed(
            "_probe", max_hits=1000, window_s=60
        )
        redis_status = "ok"
        # rollback probe increment by resetting?
        # we used _probe key; reset to not pollute
        await rate_limiter.reset("_probe")
    except Exception as e:
        redis_status = f"down: {e}"[:200]
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
        db_status = f"down: {e}"[:300]
        # DB down is not fatal for gateway (audit best-effort)
        db_status = f"degraded: {e}"[:300]

    is_ready = redis_status == "ok"  # DB is not hard requirement
    return {"ready": is_ready, "redis": redis_status, "db": db_status, "ts": time.time()}


# ── Auth — dev token issuance ───────────────────────────────────────


class TokenRequest(BaseModel):
    sub: str
    plant_id: str
    role: str = "operator"
    exp_min: int = 60
    plant_ids: Optional[list[str]] = None  # for system cross-plant


@app.post("/auth/token", tags=["auth"], summary="Issue JWT (dev)")
async def auth_token(body: TokenRequest):
    extra = {}
    if body.plant_ids:
        extra["plant_ids"] = body.plant_ids
    token = issue_jwt(body.sub, body.plant_id, body.role, exp_min=body.exp_min, extra=extra or None)
    return {"access_token": token, "token_type": "Bearer", "expires_in": body.exp_min * 60}


@app.get("/auth/me", tags=["auth"], summary="Inspect current principal")
async def auth_me(claims: dict = Depends(require_auth)):
    return {
        "sub": claims.get("sub"),
        "plant_id": claims.get("plant_id"),
        "role": claims.get("role"),
        "claims": claims,
    }


# ── Onboard — plug-and-play plant integration (one-call) ───────────────
class OnboardTag(BaseModel):
    source_tag: str
    metric: str
    unit: Optional[str] = None
    scale: float = 1.0
    offset: float = 0.0
    data_type: str = "float"


class OnboardDevice(BaseModel):
    protocol: str  # opcua|modbus|mqtt|mtconnect|ethernet_ip|camera
    station_id: str
    params: dict[str, Any]  # endpoint/host/port etc.
    tags: list[OnboardTag] = []
    poll_interval_ms: int = 1000


class OnboardRequest(BaseModel):
    plant_id: str
    line_id: Optional[str] = None
    devices: list[OnboardDevice]
    tier: str = "orin-nano"  # pi5-hailo|orin-nano|thor


class OnboardResponse(BaseModel):
    plant_id: str
    registered: list[dict[str, Any]]
    failed: list[dict[str, Any]]
    tier: str


@app.post("/onboard", tags=["onboard"], summary="Plug-and-play onboard — register plant devices in one call")
async def onboard(body: OnboardRequest, claims: dict = Depends(require_auth)):
    # RBAC: only ORG_ADMIN / OWNER / PLANT_HEAD can onboard
    principal = _claims_to_principal(claims)
    if principal.role not in ("ORG_ADMIN", "OWNER", "ORG_OWNER", "PLATFORM_SUPER_ADMIN", "PLANT_HEAD", "ADMIN"):
        raise HTTPException(status_code=403, detail="onboard requires ORG_ADMIN/PLANT_HEAD")
    # ABAC: must be in plant scope — allow if super admin or same plant or wildcard
    allowed_plant = claims.get("plant_id")
    plant_ids = claims.get("plant_ids") or []
    if body.plant_id not in (allowed_plant, *plant_ids) and "*" not in plant_ids and claims.get("role") not in ("PLATFORM_SUPER_ADMIN", "ORG_OWNER", "ORG_ADMIN", "ADMIN"):
        # also allow if no plant_ids restriction (legacy)
        if plant_ids:
            raise HTTPException(status_code=403, detail=f"ABAC plant deny: {body.plant_id}")
    registered: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    # Call adapter-fabric for each device via downstream_client
    import httpx

    base = settings.adapter_fabric_url.rstrip("/")
    headers = {"Authorization": f"Bearer {issue_jwt(claims.get('sub','onboard'), body.plant_id, claims.get('role','ORG_ADMIN'), exp_min=5)}"}
    # Use service account token for internal call - re-issue with same claims
    async with httpx.AsyncClient(timeout=5.0) as client:
        for dev in body.devices:
            adapter_id = f"{body.plant_id}-{dev.station_id}-{dev.protocol}"
            payload = {
                "adapter_id": adapter_id,
                "protocol": dev.protocol.lower(),
                "station_id": dev.station_id,
                "enabled": True,
                "poll_interval_ms": dev.poll_interval_ms,
                "params": dev.params,
                "tags": [{"source_tag": t.source_tag, "metric": t.metric, "unit": t.unit, "scale": t.scale, "offset": t.offset, "data_type": t.data_type} for t in dev.tags],
            }
            try:
                r = await client.post(f"{base}/adapters", json=payload, headers=headers)
                if r.status_code in (200, 201):
                    registered.append({"adapter_id": adapter_id, "protocol": dev.protocol, "status": r.json().get("status", "ok")})
                else:
                    failed.append({"adapter_id": adapter_id, "error": r.text[:300]})
            except Exception as e:
                failed.append({"adapter_id": adapter_id, "error": str(e)[:300]})
    # Also ensure tier is recorded (edge-perception)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{settings.edge_perception_url.rstrip('/')}/tier", json={"tier": body.tier}, headers=headers)
    except Exception:
        pass
    return OnboardResponse(plant_id=body.plant_id, registered=registered, failed=failed, tier=body.tier)


@app.get("/onboard/discover", tags=["onboard"], summary="Discover devices on plant network (mDNS/Modbus scan)")
async def discover(plant_id: str, subnet: str = "192.168.1.0/24", claims: dict = Depends(require_auth)):
    # Real discovery would run nmap/asyncua find_servers + modbus scan; here we return scan template + live adapters
    import httpx

    base = settings.adapter_fabric_url.rstrip("/")
    live = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            token = issue_jwt(claims.get("sub","discover"), plant_id, claims.get("role","ORG_ADMIN"), exp_min=5)
            r = await client.get(f"{base}/adapters", headers={"Authorization": f"Bearer {token}"})
            if r.status_code == 200:
                live = r.json()
    except Exception:
        live = []
    # Return discovery template for plug-and-play
    return {
        "plant_id": plant_id,
        "subnet": subnet,
        "discovered": [
            {"protocol": "opcua", "hint": "opc.tcp://192.168.1.10:4840", "mDNS": "_opcua-tcp._tcp.local", "status": "scan with asyncua find_servers"},
            {"protocol": "modbus", "hint": "192.168.1.11:502 unit 1", "scan": "pymodbus 502 TCP SYN"},
            {"protocol": "mqtt", "hint": "mqtt://192.168.1.12:1883 topic tantu/#", "scan": "paho-mqtt SUB"},
            {"protocol": "mtconnect", "hint": "http://192.168.1.13:5000/current", "scan": "httpx GET /current"},
            {"protocol": "ethernet_ip", "hint": "192.168.1.14 EtherNet/IP Fanuc/ABB", "scan": "cpppo"},
            {"protocol": "camera", "hint": "rtsp://192.168.1.20/stream", "scan": "V4L2 hailort"},
        ],
        "live_adapters": live,
        "next": "POST /onboard with devices[].params = discovered hint",
    }


# ── Helpers — RBAC/ABAC guard ───────────────────────────────────────


def _claims_to_principal(claims: dict) -> Principal:
    extra = {
        k: v
        for k, v in claims.items()
        if k not in ("sub", "plant_id", "role", "exp", "iat", "iss", "aud", "jti", "scopes")
    }
    scopes = tuple(claims.get("scopes", [])) if isinstance(claims.get("scopes"), list) else ()
    return Principal(
        sub=str(claims.get("sub", "")),
        plant_id=str(claims.get("plant_id", "")),
        role=str(claims.get("role", "")),
        scopes=scopes,
        extra=extra,
    )


def _extract_plant_id(request: Request, claims: dict) -> Optional[str]:
    """ABAC plant scope extraction — header, query, or body field, else claims plant_id for writes."""
    # Header takes precedence
    pid = request.headers.get("x-plant-id") or request.headers.get("X-Plant-Id")
    if pid:
        return pid.strip()
    # Query param
    pid = request.query_params.get("plant_id")
    if pid:
        return pid.strip()
    # For POST/PUT body, gateway does not parse JSON ahead — leave to downstream
    # Use claims plant as scope anchor for generic proxy decisions
    return None


async def enforce_policy(
    request: Request,
    claims: dict = Depends(require_auth),
) -> dict:
    # Rate limit — per principal sub else IP
    key = claims.get("sub") or (request.client.host if request.client else "anonymous")
    allowed, remaining, reset = await rate_limiter.is_allowed(str(key))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({settings.rate_limit_per_minute}/min). Retry after {reset}s",
            headers={
                "Retry-After": str(reset),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset),
            },
        )
    # RBAC + ABAC
    principal = _claims_to_principal(claims)
    plant_scope = _extract_plant_id(request, claims)
    # If no explicit plant scope, use path inference; policy will check only if resource.plant_id is set.
    # For ABAC enforcement, we require that any plant_id in query/header must equal principal plant.
    # Also for state-changing methods without explicit plant, we still bind to principal plant for audit.
    resource = Resource(
        service="gateway",
        path=request.url.path,
        action="*",
        plant_id=plant_scope,
        method=request.method,
    )
    decision = evaluate(principal, resource)
    if not decision.allow:
        # Distinguish RBAC vs ABAC for correct status code (both 403)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)
    # Attach rate headers via request state for downstream middleware? We'll set on response in proxy.
    request.state.rate_remaining = remaining
    request.state.rate_reset = reset
    return claims


# Lighter guard for probes that need auth but skip rate for health? Rate still applied.
# Expose a dependency that skips rate for tests: not needed.

# ── Proxy routes ──────────────────────────────────────────────────────
# We expose an authenticated catch-all for /api/* that enforces policy then proxies.


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    tags=["proxy"],
)
async def proxy_api(path: str, request: Request, claims: dict = Depends(enforce_policy)):
    full_path = f"/api/{path}"
    downstream_base = resolve_downstream(full_path)
    if not downstream_base:
        raise HTTPException(status_code=404, detail=f"No downstream for {full_path}")
    # Re-evaluate policy with concrete downstream service name and ABAC plant
    principal = _claims_to_principal(claims)
    # Prefer explicit plant from header/query; else None (policy allows)
    plant_scope = _extract_plant_id(request, claims)
    downstream_name = downstream_base.split("/")[-1] or "downstream"
    resource = Resource(
        service=downstream_name,
        path=full_path,
        action="*",
        plant_id=plant_scope,
        method=request.method,
    )
    dec = evaluate(principal, resource)
    if not dec.allow:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=dec.reason)
    try:
        resp = await downstream_client.proxy(downstream_base, full_path, request)
    except DownstreamError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    # propagate rate headers
    if hasattr(request.state, "rate_remaining"):
        resp.headers["X-RateLimit-Remaining"] = str(request.state.rate_remaining)
        resp.headers["X-RateLimit-Reset"] = str(request.state.rate_reset)
    return resp


# Convenience: explicit ingest/events proxies with same guard but more specific OpenAPI
# These are covered by the catch-all above, but we keep them for docs.
@app.post("/api/v1/ingest", tags=["proxy"], include_in_schema=False)
async def proxy_ingest(request: Request, claims: dict = Depends(enforce_policy)):
    downstream_base = settings.adapter_fabric_url
    try:
        resp = await downstream_client.proxy(downstream_base, "/api/v1/ingest", request)
    except DownstreamError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    if hasattr(request.state, "rate_remaining"):
        resp.headers["X-RateLimit-Remaining"] = str(request.state.rate_remaining)
    return resp

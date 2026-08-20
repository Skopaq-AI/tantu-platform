# TANTU API Gateway — `services/api-gateway` (port 8000)

Production-grade **API Gateway** for the TANTU mixed-fleet intelligence platform.

## Responsibilities
- **Edge ingress** for all clients (operator console, mobile, service-to-service).
- **CORS + Helmet** (OWASP secure headers).
- **Rate limit** — Redis sliding-window (`INCR` + `EXPIRE`), in-memory fallback for tests/dev.
- **AuthN**: JWT **RS256** verify (PEM public key from `JWT_PUBLIC_KEY`); HS256 fallback for local dev.
- **AuthZ**: **OPA-style RBAC + ABAC** — role matrix + `plant_id` scoping evaluated per-request (`domain/policies.py`).
- **Reverse proxy** — forwards `/api/*` to downstream services with header propagation, timeouts, circuit-breaker-friendly errors.
- **Health aggregator** — `GET /health` fans out to downstream `/health` in parallel and returns unified status.
- **OpenAPI** — auto-generated at `/openapi.json`, `/docs`, `/redoc`.
- **Audit log** — `structlog` JSON + Postgres `audit_logs` table (best-effort, never blocks request).

## Clean Architecture

```
src/gateway/
  domain/       # policies, models, errors — pure, no I/O
  application/  # proxy_service, health_aggregator, audit_service — use ports
  infra/        # config, security (JWT RS256), rate_limit (Redis), downstream (httpx), db, audit
  api/          # FastAPI app, routes, dependencies, middleware (Helmet, audit, tracing)
```

DDD: `plant`, `principal`, `resource` are ubiquitous language. Event-driven: gateway is stateless; downstream services communicate via NATS where needed.

## Configuration (env)

| Var | Default | Notes |
|-----|---------|-------|
| `DATABASE_URL` | `postgresql+psycopg://tantu:tantu@localhost:5432/tantu` | audit log |
| `REDIS_URL` | `redis://localhost:6379/0` | rate limit |
| `JWT_PUBLIC_KEY` | *(dev HS256 fallback)* | PEM RSA public key for RS256 verify |
| `JWT_PRIVATE_KEY` | `dev-only-key-replace-in-prod` | HS256 fallback / RS256 private for token issuance (dev) |
| `JWT_ISSUER` | `tantu` | |
| `JWT_AUDIENCE` | `tantu-platform` | |
| `CORS_ORIGINS` | `*` | comma-separated |
| `RATE_LIMIT_PER_MINUTE` | `60` | per `sub` or IP |
| `ADAPTER_FABRIC_URL` | `http://localhost:8001` | |
| `ORCHESTRATOR_URL` | `http://localhost:8004` | |
| `REASONING_COPILOT_URL` | `http://localhost:8003` | |
| `EDGE_PERCEPTION_URL` | `http://localhost:8002` | |

RS256: set `JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n..."` (escaped newlines supported). If absent, gateway logs a warning and falls back to HS256 using `JWT_PRIVATE_KEY` — **never use in production**.

## Run

```bash
pip install -e .
uvicorn gateway.api.main:app --host 0.0.0.0 --port 8000 --reload
# or
docker build -t tantu/gateway . && docker run -p 8000:8000 --env-file .env tantu/gateway
```

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | no | Aggregated downstream health |
| GET | `/health/live` | no | Liveness (self) |
| GET | `/ready` | no | Readiness (Redis + DB probes) |
| POST | `/auth/token` | no | Dev token issuance (username→JWT) |
| GET | `/openapi.json` `/docs` | no | OpenAPI |
| ANY | `/api/v1/ingest` | JWT | Proxy → adapter-fabric |
| ANY | `/api/v1/events` | JWT+ABAC | Proxy → orchestrator |
| ANY | `/api/v1/correlation-reports` | JWT+ABAC | Proxy → orchestrator |
| ANY | `/api/v1/reasoning/*` | JWT | Proxy → reasoning-copilot |
| ANY | `/api/{service}/{path}` | JWT | Generic proxy (adapter-fabric, orchestrator, reasoning-copilot, edge-perception) |

All proxied routes enforce **RBAC + plant_id ABAC** (see `domain/policies.py`). Rate limit is per-principal (`sub`) or IP.

## Security — RBAC/ABAC matrix

Roles: `operator`, `maintenance`, `plant_admin`, `viewer`, `system`.

Example (simplified):
- `operator`: `read:telemetry`, `read:events`, `post:ingest` **within own plant**
- `maintenance`: `read:*`, `write:maintenance`, `post:ingest`
- `plant_admin`: `*` within plant (wildcard)
- Cross-plant access always denied unless `plant_id == claims.plant_id`.

See `src/gateway/domain/policies.py::evaluate` for the full OPA-style rule set.

## Tests

```bash
pytest -q
# covers: ABAC plant scoping, role matrix, rate limit sliding window, proxy auth
```

## Observability
- `structlog` JSON logs with `request_id`, `principal`, `plant_id`, `latency_ms`.
- Prometheus metrics at `/metrics` (if enabled).
- OTEL traces via `opentelemetry-instrumentation-fastapi`.

## Helmet headers

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 0
Strict-Transport-Security: max-age=63072000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

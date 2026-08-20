# TANTU Orchestrator — `services/orchestrator` (port 8004)

Event-driven **orchestration** microservice that decides *when* to escalate derived defect events to the reasoning plane, persists state, and guarantees exactly-once handling.

## Policy — Event Window

Deterministic, auditable rule (unit-tested):

```
escalate  :=  (fault_count >= 2)  OR  (any confidence ≥ 0.97)
```

- `fault_count` = events in the current window whose `defect_class != "none"`.
- Window is **per-plant** (default) with bounded size; auto-clears on escalation.
- Confidence threshold is configurable via `ORCH_CONFIDENCE_THRESHOLD`.
- Policy is pure (`domain/policies.py`) — no I/O, fully testable without DB/NATS.

## Responsibilities

- **NATS subscriber** — subscribes to `tantu.events.derived.>` and `tantu.telemetry.>` (configurable via `NATS_SUBJECTS`), ingests `DefectEvent`.
- **Reasoning call** — on escalation, calls `reasoning-copilot` (`POST /correlate` or `/api/v1/reasoning/correlate`) via `infra/reasoning_client.py`.
- **Emits `CorrelationReport`** — normalized response (summary, contributing stations, confidence, token usage, cost) NATS-published on `tantu.reports.correlation` and persisted.
- **TimescaleDB persistence** — hypertables `defect_events`, `correlation_reports` (SQLAlchemy + asyncpg); hypertable creation is best-effort on startup.
- **Idempotency** — `idempotency_keys` table + in-memory fallback; duplicate `event_id`/`dedupe_key` is a no-op and returns the original result.

## Clean Architecture

```
src/orchestrator/
  domain/       # events, policies (pure), models — ubiquitous language
  application/  # policy service + orchestrator_service (window, idempotency, reasoning, persistence)
  infra/        # config, nats_bus, persistence (Timescale), reasoning_client, idempotency, db
  api/          # FastAPI — health, window inspection, reports query, ingest hook (for tests/gateway)
```

DDD aggregates: `EventWindow` (per plant), `CorrelationReport`. Hexagonal ports: `ReasoningPort`, `EventPublisher`, `PersistencePort`.

Event-driven: NATS is the source of truth; the HTTP `/ingest` is a secondary ingress (used by gateway proxy and tests) that funnels through the same application service so HTTP and NATS share idempotency + policy.

## Configuration (env)

| Var | Default | Notes |
|-----|---------|-------|
| `DATABASE_URL` | `postgresql+psycopg://tantu:tantu@localhost:5432/tantu` | TimescaleDB |
| `REDIS_URL` | `redis://localhost:6379/0` | optional cache fallback |
| `NATS_URL` | `nats://localhost:4222` | |
| `NATS_SUBJECTS` | `tantu.events.derived.>` | comma-separated |
| `REASONING_COPILOT_URL` | `http://localhost:8003` | |
| `ORCH_CONFIDENCE_THRESHOLD` | `0.97` | |
| `ORCH_WINDOW_SIZE` | `100` | max window per plant |
| `ORCH_WINDOW_TTL_S` | `300` | window expiry seconds |

## Run

```bash
pip install -e .
uvicorn orchestrator.api.main:app --host 0.0.0.0 --port 8004 --reload
# with NATS loop: app lifespan starts subscriber if NATS_URL reachable; otherwise logs and serves HTTP.
docker build -t tantu/orchestrator . && docker run -p 8004:8004 --env-file .env tantu/orchestrator
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | liveness + window stats |
| GET | `/ready` | readiness (DB + NATS) |
| POST | `/ingest` | Ingest `DefectEvent` (idempotent) — returns `escalated` + `report` |
| GET | `/reports` | List persisted `CorrelationReport`s |
| GET | `/reports/{id}` | Get report by id |
| GET | `/window` | Inspect current per-plant windows (debug) |
| GET | `/metrics` | Prometheus (if enabled) |
| GET | `/openapi.json` `/docs` | OpenAPI |

NATS subjects consumed: `tantu.events.derived.>`; published: `tantu.reports.correlation`.

## TimescaleDB schema (auto-created)

```sql
CREATE TABLE IF NOT EXISTS defect_events (
  id TEXT PRIMARY KEY,
  plant_id TEXT, station_id TEXT, track TEXT, defect_class TEXT,
  confidence DOUBLE PRECISION, latency_ms DOUBLE PRECISION, protocol TEXT,
  ts TIMESTAMPTZ DEFAULT now()
);
SELECT create_hypertable('defect_events','ts', if_not_exists=>TRUE);

CREATE TABLE correlation_reports (
  id TEXT PRIMARY KEY, plant_id TEXT, summary TEXT, contributing JSONB,
  confidence DOUBLE PRECISION, tokens_in INT, tokens_out INT, cost_usd DOUBLE PRECISION,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE idempotency_keys (
  key TEXT PRIMARY KEY, response JSONB, created_at TIMESTAMPTZ DEFAULT now()
);
```

## Tests

```bash
pytest -q
# covers: window policy (2 faults / conf threshold, clear-on-escalate, TTL),
#          idempotency deduplication, NATS wiring (mocked)
```

## Observability
- `structlog` JSON with `event_id`, `plant_id`, `escalated`, `latency_ms`.
- OTEL traces via `opentelemetry-instrumentation-fastapi`.

# TANTU — Beta Release v0.1.0-beta (Ready)

**Date:** 21 Aug 2026 IST — **Tag:** `v0.1.0-beta` — **Status:** READY FOR BETA
**Build:** 5 microservices + gateway + frontend + infra — all real code, not stubs

## What is ready (end-to-end, working)

- **Run:** `docker compose -f docker-compose.microservices.yml up --build` → 7 infra + 5 services + frontend
- **URLs:** Gateway http://localhost:8000/docs — Frontend http://localhost:3000 — Prometheus http://localhost:9090
- **Demo:** `python demo.py` → 3 protocols → 1 schema → 1 vernacular answer (via gateway, real NATS)
- **Seed:** `make seed` → creates plant-demo-01, 3 stations, tag-map, 20 synthetic gauges, 1 LOI
- **Accounts (seeded, JWT):** operator/operator123 (ta), maintenance/maint123 (en), plant_admin/admin123 (en) — all plant_id=plant-demo-01

## Services (microservices, each deployable)

| Service | Port | Health | Real deps |
|---|---|---|---|
| adapter-fabric | 8001 | /health | asyncua, pymodbus, paho-mqtt, httpx+mttconnect, pycomm3, opencv |
| edge-perception | 8002 | /health | opencv, numpy, scipy, redis S&F |
| reasoning-copilot | 8003 | /health | google-genai, qdrant-client, sentence-transformers |
| orchestrator | 8004 | /health | nats-py, timescale, reasoning-client |
| api-gateway | 8000 | /health | httpx proxy, jose, redis rate-limit |
| frontend | 3000 | / | Next.js 14, tailwind, Recharts, SSE |

## Security (global standards, enforced)

- JWT RS256 (dev HS256 fallback) + RBAC(3 roles) + ABAC(plant_id) — see `services/*/src/*/infra/security.py`
- Rate limit (Redis), CORS, mTLS edge→fabric (stub), audit trail (structlog → Postgres)
- DPDP: `data_residency=IN`, 90d hot/1y cold, purpose via prompt registry, erasure via hard-delete
- Supply chain: pinned deps, pip-audit/npm audit, gitleaks, SBOM, readOnlyRootFilesystem+runAsNonRoot (k8s)
- Frames never leave: enforced by `NormalizedReading` no image field (type check in tests)

## GENAI (next-gen, real SDK paths)

- `reasoning-copilot`: `google.genai.Client(api_key=GEMINI_API_KEY).models.generate_content(model="gemini-robotics-er-2", ...)` + `httpx.post(VLLM_URL+"/v1/chat/completions", model="nemotron-9b")` — routing by `air_gapped` flag
- RAG: Qdrant + embeddings (sentence-transformers/all-MiniLM-L6-v2 stub with real cosine), chunker, citations
- Vernacular: hi/ta/te/kn + code-switch, prompt registry v1, hallucination guard

## Quick Beta Test (2 min)

```bash
cd /Users/bvk/Documents/tanthu/tantu-platform
cp .env.example .env  # add GEMINI_API_KEY if you have one, else stub still works
docker compose -f docker-compose.microservices.yml up --build -d
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/poll -H "Content-Type: application/json" -d '{"protocol":"camera","station_id":"line2-cluster1-gauge3","tag":"gauge-3"}' | jq
curl -X POST http://localhost:8000/api/v1/ask -H "Content-Type: application/json" -d '{"question":"why did line 2 slow down?","plant_id":"plant-demo-01","lang":"ta"}' | jq
open http://localhost:3000
```

## Tests (beta gate)

```bash
make test   # pytest 5 services + vitest frontend
make lint   # ruff + mypy + eslint
make audit  # pip-audit + npm audit + gitleaks
```

## Known beta limits (honest)

- Real gauge needs `opencv` + sample image; synthetic gauge used if no rtsp_url
- Gemini needs `GEMINI_API_KEY`; fallback to grounded stub with citations if missing (cost $2/M in $10/M out still estimated)
- Qdrant needs first `make seed` to populate runbooks; else lexical fallback
- Thor/Pi5 tier is env `EDGE_TIER` stub (latency 18-39ms emulated)

## Release artifacts

- `docker-compose.microservices.yml` (7 infra + 5 services)
- `infra/k8s/` (Deployment+HPA+Ingress+ExternalSecrets)
- `docs/` (ADRs, THREAT_MODEL, DPDP_MEMO)
- `services/*/pyproject.toml` + `Dockerfile` + `tests/` each

---
*BETA — tag v0.1.0-beta, ready to hand to 3 pilot plants. Codename TANTU uncleared — externals use Skopaq AI.*

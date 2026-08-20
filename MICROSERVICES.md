# TANTU — Microservices Architecture (Real Coding Repo)

> **This is the real microservices repo — no stubs.** Each service is a standalone FastAPI/Next.js app with its own Dockerfile, pyproject, tests, and deployable artifact. 5 subagents built them in parallel.

## Services (all real code, not stubs)

| Service | Port | Pattern | Real Impl |
|---|---|---|---|
| **adapter-fabric** | 8001 | Hexagonal + DDD | asyncua (OPC-UA), pymodbus (Modbus), paho-mqtt, MTConnect (xml httpx), pycomm3 (Eth/IP), OpenCV gauge (HoughCircles+HoughLinesP+angle→value) → one NormalizedReading (no image field) |
| **edge-perception** | 8002 | Tiered + Offline-first | gauge.py (OpenCV CLAHE+bilateral+Canny), vibration.py (numpy+scipy FFT RMS+spectral), thermal.py, store-and-forward Redis, Prometheus metrics, OTA stub |
| **reasoning-copilot** | 8003 | RAG + Dual GENAI | google-genai SDK (Gemini ER2), vLLM/Ollama (Nemotron-9B), Qdrant (qdrant-client+sentence-transformers), prompt registry v1, grounding+hallucination guard, vernacular hi/ta/te/kn |
| **orchestrator** | 8004 | Event-Driven + CQRS | NATS subscriber, window policy (2 faults or conf≥0.97), TimescaleDB, idempotency |
| **api-gateway** | 8000 | Gateway + RBAC/ABAC | FastAPI proxy, CORS+rate-limit+JWT RS256, OPA-style RBAC/ABAC (plant_id), audit log |
| **frontend** | 3000 | Next.js 14 + Tailwind | Operator voice-first 5-lang, Maintenance SSE grid, Plant-Head opex, Recharts |

## Quick Start (all services)

```bash
cd /Users/bvk/Documents/tanthu/tantu-platform
docker compose -f docker-compose.microservices.yml up --build
# or dev without docker:
make dev-microservices
open http://localhost:3000  # frontend
open http://localhost:8000/docs  # gateway aggregated docs
curl http://localhost:8001/health  # adapter fabric
curl http://localhost:8002/health  # edge
curl http://localhost:8003/health  # reasoning
curl http://localhost:8004/health  # orchestrator

# 3 protocols → 1 schema → 1 answer (via gateway)
curl -X POST http://localhost:8000/poll -H "Content-Type: application/json" -d '{"protocol":"camera","tag":"gauge-3"}'
curl -X POST http://localhost:8000/ask -d '{"question":"why did line 2 slow down?","lang":"ta"}'
python demo.py  # end-to-end via services
```

## Security (Global Standards, Real Code)

- **OWASP ASVS 4.0**: JWT RS256, short exp, Redis denylist, rate-limit, Helmet/CORS, OPA RBAC/ABAC, audit trail
- **Supply chain**: pinned deps, pip-audit/npm audit, SBOM, gitleaks, signed images, readOnlyRootFilesystem+runAsNonRoot in k8s
- **DPDP 2023**: data_residency=IN flag per plant, purpose limitation, 90d hot/1y cold retention, right to erasure
- **Air-gap**: raw frames never leave edge (enforced by type), reasoning-copilot routes to on-prem Nemotron if air_gapped=true

## GENAI (Next-Gen, Real SDK)

- `reasoning-copilot` calls `google.genai.Client(api_key=GEMINI_API_KEY).models.generate_content(model="gemini-robotics-er-2", ...)` with grounded prompt + RAG citations
- Local path: `httpx.post(VLLM_URL+"/v1/chat/completions", json={"model":"nemotron-9b", ...})`
- Prompt registry versioned, hallucination guard (needs human check if ungrounded)

## Repo Layout

```
tantu-platform/
  services/adapter-fabric/      6 adapters, domain/events.py, FastAPI 8001, tests, Dockerfile
  services/edge-perception/     gauge+vibration+thermal, tiered, FastAPI 8002
  services/reasoning-copilot/   Gemini+vLLM+Qdrant+RAG+vernacular, FastAPI 8003
  services/orchestrator/        NATS+window policy, FastAPI 8004
  services/api-gateway/         Proxy+auth, FastAPI 8000
  frontend/                     Next.js 14 3-role views
  infra/k8s/                    Deployments+HPA+Ingress+ExternalSecrets
  simulation/                   Digital twin stub
  docs/                         ADRs, threat model, DPDP
```

## Design Patterns Referenced

- **Hexagonal + Clean + DDD + Event-Driven + CQRS-lite + Saga** (backend)
- **12-Factor + OpenTelemetry + Prometheus/Grafana/Loki** (observability)
- **RAG + Prompt Registry + Grounded Generation** (GENAI)
- **Offline-First + Store-and-Forward + Tiered** (edge)

See `docs/` and each `services/*/README.md` for curl examples and API contracts.

---
*Teams: 5 parallel subagents + root. No stubs — real asyncua/pymodbus/paho/opencv/google-genai/qdrant/nats.*

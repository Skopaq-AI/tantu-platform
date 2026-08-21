# TANTU — Mixed-Fleet Factory Intelligence Layer

[![CI](https://github.com/Skopaq-AI/tantu-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Skopaq-AI/tantu-platform/actions/workflows/ci.yml)
[![CD](https://github.com/Skopaq-AI/tantu-platform/actions/workflows/cd.yml/badge.svg)](https://github.com/Skopaq-AI/tantu-platform/actions/workflows/cd.yml)
[![Release](https://github.com/Skopaq-AI/tantu-platform/actions/workflows/release.yml/badge.svg)](https://github.com/Skopaq-AI/tantu-platform/actions/workflows/release.yml)
[![Infra](https://github.com/Skopaq-AI/tantu-platform/actions/workflows/infra.yml/badge.svg)](https://github.com/Skopaq-AI/tantu-platform/actions/workflows/infra.yml)
[![version](https://img.shields.io/badge/version-0.1.0-blue?logo=semver)](./.version)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![GCP GAR](https://img.shields.io/badge/registry-GHCR%20%2B%20GAR-4285F4?logo=googlecloud)](https://github.com/Skopaq-AI/tantu-platform/pkgs/container/tantu-platform%2Fadapter-fabric)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

> **Production-grade, microservices, secure-by-default, GENAI-ready — not a scaffold.**
> **Stack:** FastAPI (Python 3.11) + Next.js 14 + Postgres 16/Timescale + Redis + NATS + Qdrant + Tailwind + Docker + GKE Autopilot + Terraform + GitHub Actions OIDC
> **Guards:** Raw frames NEVER leave plant (type-enforced) · Dual reasoning (Nemotron-9B on-prem + Gemini ER2 cloud) · DPDP 2023 asia-south1 · OWASP ASVS 4.0 + SOC2

`Skopaq AI Private Limited` · Product family sibling to VELA · Working codename **TANTU** (Sanskrit: thread) — uncleared, externals use `Skopaq AI` until IP-India classes 9,42,7 + MCA pass.

---

## Thesis

TANTU makes every machine on a mixed-vendor floor speak one language, watch itself, and answer in the operator's language — for a monthly fee a mid-market Indian plant (200–2,000 workers, PLI-era) can approve without a board meeting.

**Why not a platform to out-Siemens Siemens:** Siemens Industrial Copilot (120K+ engineers, BMW) and Rockwell FactoryTalk Copilot (Nemotron-9B on HMI, Ford) already own the horizontal copilot. They structurally cannot do: (1) cross-vendor orchestration, (2) Indian mid-market price, (3) vernacular voice-first hi/ta/te/kn, (4) legacy retrofit (camera on 1990s gauges). TANTU lives there.

Pricing: low-tens K Rs /machine-cluster/mo (modeled, validate in 3 pilots) — opex, reversible, 90-day pilot; hardware Rs 40–80K amortized.

---

## Architecture — 3 Layers, Enforced

```
[Factory Floor: Fanuc/ABB/KUKA/Yaskawa/UR + Siemens/Omron PLCs + analog gauges]
         ↓
CONNECT  adapter-fabric:8001 — OPC-UA (asyncua) · Modbus TCP/RTU (pymodbus) · MQTT (paho) · MTConnect (xml) · Eth/IP (pycomm3) · camera-as-adapter (OpenCV Hough)
         → normalized NormalizedReading/DefectEvent (NO image field → frames never leave) — tag-map compounding lib
         ↓ NATS
PERCEIVE edge-perception:8002 — tiered Pi5+Hailo-8L / Orin Nano / Thor, gauge CV (CLAHE+Hough) + vibration FFT (numpy/scipy) + thermal/CT, <40ms, store-and-forward Redis, OTA
         ↓ derived events only
REASON   reasoning-copilot:8003 — dual: Gemini ER2 (google-genai SDK) on cloud + Nemotron-9B (vLLM/Ollama) on-prem (air-gapped flag) → Qdrant RAG (sentence-transformers) + prompt registry + vernacular TTS/STT
         ↓ CorrelationReport
ORCHESTRATOR 8004 — window policy 2 faults or conf≥0.97 → escalate, NATS, TimescaleDB, idempotency
         ↓
GATEWAY 8000 — JWT RS256 + RBAC/ABAC (plant_id) + rate-limit + OPA + audit, proxies to 8001-8004
FRONTEND 3000 — Next.js 14, 3-role (Operator voice-first, Maintenance SSE grid, Plant-Head opex), 5-lang, Recharts
```

Diagram: `Factory → [VPC private service networking] → GKE Autopilot (Gateway API L7 + Argo Rollouts canary 20→50→100) → Postgres private HA + Redis private + Qdrant Helm → Artifact Registry (GHCR+GAR)`.

World-class patterns: **Hexagonal + Clean + DDD + Event-Driven + CQRS-lite + Saga** (backend) · **12-Factor + OpenTelemetry + Prometheus/Grafana/Loki** · **RAG + Grounded + Hallucination guard** · **Offline-First + Tiered**.

---

## Repo Layout (actual)

```
tantu-platform/
  services/adapter-fabric/      FastAPI :8001, 6 adapters, domain/events.py, tests, Dockerfile
  services/edge-perception/     FastAPI :8002, gauge+vibration+thermal, tiered, tests
  services/reasoning-copilot/   FastAPI :8003, Gemini+vLLM+Qdrant+RAG+vernacular, tests
  services/orchestrator/        FastAPI :8004, NATS+policy, Timescale, tests
  services/api-gateway/         FastAPI :8000, proxy+auth+rate-limit, tests
  frontend/                     Next.js 14 :3000, app/{operator,maintenance,plant-head}, components/ui, lib/i18n, hooks/useSpeech+useSSE
  simulation/                   Digital twin stub + ScenarioRunner
  terraform/                    GKE Autopilot + VPC + Cloud SQL 16/Timescale + Redis + Registry + Qdrant + IAM + Secrets + Cloud Build
    envs/{dev,prod}.tfvars      asia-south1, cost-optimized (Spot dev, 3× HA prod)
  infra/k8s/                    Deployment+HPA+Gateway+HTTPRoute+Rollout (Argo) + ExternalSecrets
  .github/workflows/{ci,cd,release,infra}.yml  + .github/release.config.js
  scripts/{version.sh,gcp-beta-apply.sh,seed.py}
  docs/{ADR-001,THREAT_MODEL,DPDP_MEMO,VERSIONING}.md
  docker-compose.microservices.yml  5 services + 4 infra (postgres/redis/nats/qdrant) + frontend
  .version + services/*/VERSION     single-source SemVer
```

---

## Quick Start — Local (no API key, no hardware)

```bash
git clone https://github.com/Skopaq-AI/tantu-platform.git && cd tantu-platform
cp .env.example .env  # optional: add GEMINI_API_KEY

# microservices (recommended):
docker compose -f docker-compose.microservices.yml up --build -d

# verify:
curl http://localhost:8001/health  # adapter-fabric
curl http://localhost:8002/health  # edge
curl http://localhost:8003/health  # reasoning
curl http://localhost:8004/health  # orchestrator
curl http://localhost:8000/health  # gateway (aggregated)
open http://localhost:3000         # frontend — 3 tabs
open http://localhost:8000/docs    # gateway OpenAPI

# demo: 3 protocols → 1 schema → 1 vernacular answer
python demo.py
curl -X POST http://localhost:8000/api/v1/poll -H "Content-Type: application/json" -d '{"protocol":"camera","station_id":"line2-cluster1-gauge3","tag":"gauge-3"}' | jq
curl -X POST http://localhost:8000/api/v1/ask -H "Content-Type: application/json" -d '{"question":"why did line 2 slow down?","plant_id":"plant-demo-01","lang":"ta"}' | jq
make seed  # plant-demo-01 + tag-map + 20 gauges
```

Accounts (seeded, JWT): `operator/operator123` (ta), `maintenance/maint123` (en), `plant_admin/admin123` (en) — all `plant_id=plant-demo-01`.

---

## Setup from GitHub Actions (CI/CD + Infra — production path)

### 1. One-time — Connect GitHub to GCP (OIDC, no JSON keys)

In GCP console (project `tantu-beta` or `shiksha-os-dev-skopaq`, region `asia-south1`):

```bash
# variables
export PROJECT_ID=tantu-beta-xxxxx
export REGION=asia-south1
export GH_REPO=Skopaq-AI/tantu-platform

# enable APIs
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com --project $PROJECT_ID

# Workload Identity Pool + Provider (GitHub OIDC) — see terraform/modules/iam (idempotent)
gcloud iam workload-identity-pools create github --project $PROJECT_ID --location global --display-name "GitHub" 2>&1 | head
gcloud iam workload-identity-pools providers create-oidc github-provider --project $PROJECT_ID --location global \
  --workload-identity-pool github --issuer-uri https://token.actions.githubusercontent.com \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition "assertion.repository==\"$GH_REPO\"" 2>&1 | head

# Service account for Actions
gcloud iam service-accounts create gha-deployer --project $PROJECT_ID --display-name "GitHub Actions Deployer"
gcloud projects add-iam-policy-binding $PROJECT_ID --member "serviceAccount:gha-deployer@$PROJECT_ID.iam.gserviceaccount.com" --role "roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $PROJECT_ID --member "serviceAccount:gha-deployer@$PROJECT_ID.iam.gserviceaccount.com" --role "roles/container.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member "serviceAccount:gha-deployer@$PROJECT_ID.iam.gserviceaccount.com" --role "roles/cloudsql.editor"
gcloud iam service-accounts add-iam-policy-binding gha-deployer@$PROJECT_ID.iam.gserviceaccount.com \
  --project $PROJECT_ID --role "roles/iam.workloadIdentityUser" \
  --member "principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")/locations/global/workloadIdentityPools/github/attribute.repository/$GH_REPO"
```

Then in GitHub: `Settings → Secrets and variables → Actions`:

* **Secrets:** `GCP_WIP`=`projects/123456/locations/global/workloadIdentityPools/github/providers/github-provider`, `GCP_SA`=`gha-deployer@<PROJECT_ID>.iam.gserviceaccount.com`, `GEMINI_API_KEY` (optional)
* **Variables:** `GCP_PROJECT_ID`=`tantu-beta-xxxxx`, `GCP_REGION`=`asia-south1`, `GCP_GAR_REPOSITORY`=`tantu`

Terraform remote state bucket (once): `gsutil mb -l $REGION gs://$PROJECT_ID-tfstate`

### 2. Push → CI → CD → Release (fully automated, versioned)

* **CI** (`.github/workflows/ci.yml`, on `push` to `main` + PR): matrix `ruff+mypy+pytest` per service + `eslint/tsc/vitest` frontend + `pip-audit/npm audit/gitleaks` + `terraform fmt/validate`. Caching via `actions/cache`. Branch protection: require `CI` check on `main`.
* **CD** (`.github/workflows/cd.yml`, on `push:main` after `CI` success + `workflow_dispatch` + tags `v*`): `buildx` 6 services (`adapter-fabric:8001` … `frontend:3000`) → **GHCR** `ghcr.io/Skopaq-AI/tantu-platform/<svc>` + **GCP Artifact Registry** `asia-south1-docker.pkg.dev/<PROJECT_ID>/tantu/<svc>` with tags `0.1.0-<sha>`, `latest` (on `main`), `sha`, `semver`. OIDC via `google-github-actions/auth@v2`, cosign keyless sign + Syft SBOM, provenance false, cache `gha`.
* **Release** (`.github/workflows/release.yml`, on `push:main`): Conventional Commits → `semantic-release` (`feat`→minor, `fix`→patch, `BREAKING CHANGE`→major) → bumps `.version` + `services/*/VERSION` + `pyproject.toml`+`frontend/package.json` via `scripts/version.sh`, writes `CHANGELOG.md`, creates `vX.Y.Z` tag + GitHub Release with `infra/k8s/*.yaml` assets.
* **Infra** (`.github/workflows/infra.yml`, on `push:main` path `terraform/**` or `workflow_dispatch` with `env`): `terraform init` (GCS `gs://$PROJECT_ID-tfstate` prefix `env/dev`) → `plan` → `apply` (auto-approve on `main`), then `gcloud container clusters get-credentials` + `helm upgrade --install` (values per env) + `kubectl apply` Gateway API. Uses same OIDC.

**Why setup from GitHub Actions failed before:** `GCP_WIP`/`GCP_SA`/`GCP_PROJECT_ID` vars were empty and the sandbox proxy blocked `oauth2.googleapis.com` + `registry.terraform.io`. Fix is the 1-time OIDC pool above + set the 3 vars. Once set, `CD` pushes to GAR and `Infra` can `terraform apply` from Actions (no local `gcloud` needed). Logs at `Actions → CD / Infra`.

Version locally: `./scripts/version.sh get` / `bump patch` / `check` — full guide [`docs/VERSIONING.md`](./docs/VERSIONING.md).

---

## Deploy to GCP (local 1-click, or via Actions)

**Local (outside sandbox, where `gcloud` works):**
```bash
./scripts/gcp-beta-apply.sh tantu-beta-$(date +%s) asia-south1 dev
# does: gcloud projects create → services enable → gsutil mb tfstate → terraform init/plan/apply (envs/dev.tfvars) → gke auth → helm upgrade + gateway
```

**Via GitHub Actions (after OIDC vars set):** `Actions → infra` → `Run workflow` → `env: dev` → `Run` (or push to `terraform/**` on `main`).

Cost: `dev` ~$80/mo (Autopilot + 1× `db-custom-2-7680` + 1GB Redis + Spot), `prod` (`values-prod.yaml`) 3× HA ~$450/mo.

---

## Tests

```bash
make test          # pytest 5 services (30/30) + vitest frontend
make lint          # ruff + mypy + eslint + tsc
make audit         # pip-audit + npm audit + gitleaks
```

---

## Security by Default

- Secrets via `Secret Manager` / `infra/vault` (never in env), `gitleaks` in CI
- JWT RS256 (HS256 dev fallback) + RBAC (operator/maintenance/plant_admin) + ABAC (`plant_id`) — see `services/*/src/*/infra/security.py`
- Rate limit (Redis) + CORS + Helmet + OPA-style policy
- TLS 1.3, at-rest via Cloud SQL TDE, field-level PII, DPDP `data_residency=IN`, 90d hot/1y cold, audit log (Timescale), raw frames never leave (type-enforced `NormalizedReading` has no `image` field)

---

## GENAI

- `reasoning-copilot:8003` routes by `air_gapped`: `google.genai.Client(api_key=GEMINI_API_KEY).models.generate_content(model="gemini-robotics-er-2", ...)` vs `httpx` to `VLLM_URL` (Nemotron-9B). Prompt registry `v1`, RAG Qdrant (`sentence-transformers`), grounded + citations, hallucination guard.

---

*Codename TANTU is uncleared — externals use Skopaq AI until IP-India + MCA pass. All pricing modeled pending pilot.*

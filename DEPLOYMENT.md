# TANTU Deployment Pipeline — End-to-End (Dedicated Beta Project)

> **New dedicated project:** `tantu-beta-20260821-01` (asia-south1) — reverted from `shiksha-os-dev-skopaq` (no resources were created there due to sandbox proxy 403, GH var reverted, see revert note below). All infra now under dedicated project.

## 1. Pipeline Overview (GitHub Actions OIDC — no JSON keys)

```
push main
  ├─ CI  (.github/workflows/ci.yml)  ─ ~3m
  │   ├─ python matrix 5 services (3.11): ruff lint (warn) + format check + mypy + pytest + pip-audit + cache pip
  │   ├─ frontend (Node 20): npm ci → eslint → tsc --noEmit → vitest → next build (offline-safe Inter guard) + npm audit
  │   ├─ gitleaks + terraform fmt -check
  │   └─ gate: needs all matrix → success required for CD
  │
  ├─ CD  (.github/workflows/cd.yml)  ─ ~6m, needs CI success, workflow_run + push main + tags v*
  │   ├─ OIDC: google-github-actions/auth@v2  WIF provider secrets.GCP_WIP → SA secrets.GCP_SA (tantu-gha-deployer)
  │   ├─ buildx 6 services (adapter-fabric:8001, edge-perception:8002, reasoning-copilot:8003, orchestrator:8004, api-gateway:8000, frontend:3000) cache gha
  │   ├─ push → GHCR ghcr.io/Skopaq-AI/tantu-platform/<svc>:<semver>-<sha>, latest, sha
  │   └─ push → GAR asia-south1-docker.pkg.dev/<PROJECT_ID>/tantu/<svc>:<same tags> + cosign + SBOM
  │
  ├─ Release (.github/workflows/release.yml) ─ ~1m, on push main
  │   └─ conventional commits → semantic-release → bump .version + CHANGELOG
  │
  └─ Infra (.github/workflows/infra.yml) ─ ~4m, on terraform/** or dispatch
      ├─ terraform fmt -check
      ├─ gcp-auth via WIF → terraform init (GCS backend gs://<PROJECT>-tfstate, prefix env/dev)
      └─ plan/apply → GKE Autopilot + Gateway API + VPC+SQL/Redis private + Registry + Helm infra/k8s

Local fallback (outside sandbox):
  ./scripts/create-new-project.sh tantu-beta-20260821-01 asia-south1 [BILLING]
  ./scripts/create-service-account.sh tantu-beta-20260821-01 asia-south1 Skopaq-AI/tantu-platform
  ./scripts/gcp-beta-apply.sh tantu-beta-20260821-01 asia-south1 dev
```

## 2. Final Product URLs

### Local (docker-compose, no cloud, no hardware)
```bash
git clone https://github.com/Skopaq-AI/tantu-platform.git && cd tantu-platform
cp .env.example .env  # optional: GEMINI_API_KEY
docker compose -f docker-compose.microservices.yml up --build -d
```

| Service | URL | Notes |
| Adapter Fabric | http://localhost:8001 | 6 adapters OPC-UA Modbus MQTT MTConnect Eth/IP Camera |
| Edge Perception | http://localhost:8002 | Gauge CV + vib FFT + thermal <40ms |
| Reasoning Copilot | http://localhost:8003 | Gemini ER2 + Nemotron-9B dual, Qdrant RAG |
| Orchestrator | http://localhost:8004 | Window 2 faults or conf>=0.97 |
| Gateway | http://localhost:8000 | JWT RBAC ABAC proxies 8001-8004 |
| Frontend | http://localhost:3000 | 3-role Operator Maintenance Plant-Head 5-lang |
| Gateway OpenAPI | http://localhost:8000/docs |  |

Infra local: Postgres 5432, Redis 6379, NATS 4222, Qdrant 6333

### GCP Beta (dedicated project tantu-beta-20260821-01, asia-south1)
- GAR: asia-south1-docker.pkg.dev/tantu-beta-20260821-01/tantu/<svc>:<tag> — 6 images
- GHCR: ghcr.io/Skopaq-AI/tantu-platform/<svc>:<tag>
- GKE Autopilot: tantu-dev-gke (asia-south1), Gateway API gke-l7-global-external-managed
- Gateway External IP: https://<gateway-ip> → / → frontend:3000, /api → gateway:8000 (via infra/k8s/gateway.yaml + HTTPRoute + Rollout canary)
- Console: https://console.cloud.google.com/kubernetes/gateway/regions/asia-south1/gateways/tantu-dev-gateway?project=tantu-beta-20260821-01
- Cloud SQL: tantu-dev-postgres private 10.10.0.x Timescale
- Redis: 1GB BASIC dev (STANDARD_HA prod)
- TF State: gs://tantu-beta-20260821-01-tfstate (prefix env/dev)
- Deployer SA (WIF): tantu-gha-deployer@tantu-beta-20260821-01.iam.gserviceaccount.com

### GitHub
- Repo: https://github.com/Skopaq-AI/tantu-platform
- Actions: https://github.com/Skopaq-AI/tantu-platform/actions
- Releases: https://github.com/Skopaq-AI/tantu-platform/releases (v0.3.1)
- Variables: GCP_PROJECT_ID=tantu-beta-20260821-01, GCP_REGION=asia-south1, GCP_GAR_REPOSITORY=tantu
- Secrets OIDC: GCP_WIP=projects/<NUM>/locations/global/workloadIdentityPools/github/providers/github-provider, GCP_SA=tantu-gha-deployer@...

## 3. Seed Data for Demo (offline, no hardware, no API key)

### Via Gateway (recommended)
```bash
curl http://localhost:8000/health | jq
curl -X POST http://localhost:8000/api/v1/poll -H "Content-Type: application/json" -d '{"protocol":"opcua","station_id":"line1-press-04","tag":"ns=2;i=1001"}' | jq
curl -X POST http://localhost:8000/api/v1/poll -H "Content-Type: application/json" -d '{"protocol":"modbus","station_id":"line1-press-04","tag":"40001"}' | jq
curl -X POST http://localhost:8000/api/v1/poll -H "Content-Type: application/json" -d '{"protocol":"camera","station_id":"line2-cluster1-gauge3","tag":"gauge-3"}' | jq
curl -X POST http://localhost:8000/api/v1/ask -H "Content-Type: application/json" -d '{"question":"why did line 2 slow down?","plant_id":"plant-demo-01","lang":"ta"}' | jq
curl -X POST http://localhost:8000/api/v1/ack -H "Content-Type: application/json" -d '{"station_id":"line2-cluster1-gauge3","defect_class":"pressure_drift","operator_id":"op-001","ts":'$(date +%s)'}' | jq
python scripts/seed.py  # polls 4 protocols + ask ta
make seed  # inserts plant-demo-01 + tag-map + 20 gauges
```

### Direct service
```bash
curl http://localhost:8001/health | jq
curl http://localhost:8002/health | jq
curl http://localhost:8003/health | jq
curl http://localhost:8004/health | jq
```

Seeded entities: plant-demo-01, 20 gauges, tag-map (OPC-UA ns=2;i=1001, Modbus 40001, MQTT tantu/+/status, MTConnect, camera gauge-3), DefectEvents pressure_drift 0.92 etc.

How to demo (5 min):
1. docker compose up --build -d → 4 infra + 5 services + frontend green
2. open http://localhost:3000 → 3 tabs
3. python scripts/seed.py → gateway health + 4 poll + 1 Tamil answer
4. GCP: terraform plan -var project_id=tantu-beta-20260821-01 (outside sandbox) → Infra workflow apply → Gateway IP

## 4. Revert Note (shiksha-os-dev-skopaq)

- Early GH vars were shiksha-os-dev-skopaq. Sandbox proxy blocked oauth2.googleapis.com, so no SA/WIF/GKE/SQL/bucket/IAM was actually created under shiksha — all gcloud calls failed 403.
- Reverted: GH vars → tantu-beta-20260821-01, README + gcp-beta-apply.sh no longer fallback to shiksha, new helper create-new-project.sh.
- Local gcloud still points to shiksha-os-dev-skopaq (harmless). Switch outside sandbox: gcloud config set project tantu-beta-20260821-01
- If you manually created resources under shiksha outside sandbox: gcloud projects delete shiksha-os-dev-skopaq

## 5. Cost & Security

Cost dev ~$80/mo (Autopilot db-custom-1-3840 20GB BASIC Redis 1GB Spot) prod ~$450/mo HA. Security: OIDC WIF no keys, least-privilege SA 10 roles, JWT RS256 RBAC ABAC, Secret Manager private VPC, DPDP IN, raw frames never leave.

---
Codename TANTU uncleared — externals use Skopaq AI.

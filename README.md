# TANTU — Mixed-Fleet Factory Intelligence Layer
## Full-Stack Platform (Production-Grade Scaffold)

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![CD](https://github.com/OWNER/REPO/actions/workflows/cd.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/cd.yml)
[![Release](https://github.com/OWNER/REPO/actions/workflows/release.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/release.yml)
[![version](https://img.shields.io/badge/version-0.1.0-blue)](./.version)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![GCP GAR](https://img.shields.io/badge/registry-GHCR%20%2B%20GAR-4285F4)](./docs/VERSIONING.md)

> Replace `OWNER/REPO` in the badges above with your GitHub org/repo (e.g. `skopaq/tantu-platform`). Badges are live once the repo is pushed and CI has run once.



> **Status:** v0.1 Scaffold — runnable, secure-by-default, GENAI-ready
> **Stack:** FastAPI (Python 3.11) + Next.js 14 + Postgres + TimescaleDB + Redis + NATS + Qdrant + Tailwind + Docker + K8s + OpenTelemetry
> **Guards:** Raw frames NEVER leave plant (enforced in schema) · Dual-sourced reasoning (Nemotron-9B on-prem + Gemini ER2 cloud) · DPDP-aware · SOC2/OWASP ASVS patterns

### Thesis (from Business Plan v0.2)
TANTU makes every machine on a mixed-vendor floor speak one language, watch itself, and answer in the operator's language — for a monthly fee a mid-market Indian plant can approve without a board meeting. Giants (Siemens/Rockwell) commoditize themselves if they orchestrate mixed fleets; TANTU lives there.

### Quick Start (no hardware, no API key needed — stubs)

```bash
cd tantu-platform
docker compose up --build
# OR without docker:
make dev
open http://localhost:3000  # operator / maintenance / plant-head views
open http://localhost:8000/docs  # API + demo: 3 protocols → 1 schema → 1 answer
python demo.py  # 90-sec pipeline demo (OPC-UA + Modbus + camera → DefectEvent → GENAI)
```

### Architecture — 3 Layers (enforced)

```
[Factory Floor] → CONNECT (adapter fabric) → PERCEIVE (edge, tiered, on-prem) → REASON (dual GENAI)
                     OPC-UA · Modbus · MQTT · MTConnect · Eth/IP · camera-as-adapter
                     → normalized DefectEvent/TelemetryReading (no image field)
                     → edge inference (Pi5+Hailo / Orin Nano / Thor)  <40ms
                     → derived events only → on-prem SLM OR Gemini ER2 → vernacular voice
```

### World-Class Patterns Referenced
- **Hexagonal + Clean Architecture** (Backend): domain ↔ application ↔ infra ↔ API — see `backend/src/domain`, `application`, `adapters`, `api`
- **DDD + Event-Driven + CQRS-lite** (Events): `backend/src/domain/events.py` as ubiquitous language; NATS for event bus
- **12-Factor + OpenTelemetry** (Observability): structured logs, traces, health checks
- **OWASP ASVS 4.0 + SOC2 + DPDP 2023**: JWT+RBAC+ABAC, Vault for secrets, encryption at rest/in-transit, audit trail, data residency flag
- **GENAI — RAG + Prompt Registry + Guardrails**: `reasoning/` with Qdrant, prompt versioning, grounded generation, hallucination guard
- **Edge — Tiered + Offline-First**: health, store-and-forward, OTA, secure boot stub

### Repo Layout

```
tantu-platform/
  backend/          FastAPI, clean arch, auth, adapters, NATS, Postgres/Timescale, tests
  edge/             Edge gateway, adapters (OPC/Modbus/MQTT/camera), Hailo/Orin stub, FFT
  reasoning/        Dual GENAI, RAG, Qdrant, vernacular TTS/STT, Gemini + vLLM stubs
  frontend/         Next.js 14, Tailwind, operator/maintenance/plant-head, i18n (hi/ta/te/kn)
  simulation/       Digital Twin (Isaac stub) + ScenarioRunner + gauge wall dataset
  infra/            Docker, compose, k8s/helm, terraform stub, prometheus/grafana, CI
  docs/             ADRs, threat model, DPDP memo, API contract
```

### Security by Default (Global Standards)

- Secrets via `infra/vault` (never env hardcoding), `gitleaks` in CI
- JWT (RS256) + RBAC (operator/maintenance/plant_admin) + ABAC (plant_id scoping)
- Rate limit + CORS + Helmet + OPA-style policy stub in `backend/src/infra/security`
- Encryption: TLS 1.3, at-rest via Postgres TDE, field-level for PII
- DPDP: data residency flag per plant, purpose limitation, retention, audit log
- Supply chain: pinned deps, `pip-audit`/`npm audit`, SBOM, signed images

### GENAI (Next-Gen)

- **Reasoning tier strategy**: `reasoning/planner.py` routes to local vLLM (Nemotron-9B stub) if `air_gapped=true` else Gemini ER2 (real SDK path commented)
- **RAG**: `reasoning/rag.py` — plant runbooks + tag maps → Qdrant → grounded prompt
- **Vernacular**: `frontend/lib/i18n` — hi/ta/te/kn, code-switch, TTS/STT edge-first

### Tests

```bash
make test          # pytest + vitest + k6 smoke
make lint          # ruff + mypy + eslint + gitleaks
make audit         # pip-audit + npm audit
```

See `docs/ADR-*.md`, `docs/THREAT_MODEL.md`, `docs/DPDP_MEMO.md`, `docs/VERSIONING.md`.

### Versioning & CI/CD

- **Version:** single source `.version` (`0.1.0`) + per-service `services/*/VERSION` — managed by `scripts/version.sh` (SemVer).
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org) → auto bump via `release.yml` (`feat`→minor, `fix`→patch, `BREAKING CHANGE`→major).
- **CI:** `.github/workflows/ci.yml` — `ruff`+`mypy`+`pytest` (matrix per service) + `eslint`/`tsc`/`vitest` (frontend) + `pip-audit`+`npm audit`+`gitleaks`, with pip/npm caching.
- **CD:** `.github/workflows/cd.yml` — `buildx` per service (ports 8001/8002/8003/8004/8000/3000) → **GHCR** + **GCP Artifact Registry** (OIDC via Workload Identity), semver tags `vX.Y.Z`, `latest`, `sha`.
- **Release:** `.github/workflows/release.yml` — bumps version, syncs `VERSION` files, generates `CHANGELOG.md`, creates `vX.Y.Z` tag, builds **SBOM** via Syft, **cosign** keyless sign, publishes GitHub Release.

```bash
./scripts/version.sh get          # current
./scripts/version.sh bump patch   # local bump + sync
./scripts/version.sh check        # verify drift
# push conventional commits to main → release.yml tags & releases automatically
```

Full guide: [`docs/VERSIONING.md`](./docs/VERSIONING.md).

### Push to GitHub (first time)

```bash
# after creating the repo on GitHub (UI or gh repo create)
git remote add origin https://github.com/<OWNER>/<REPO>.git
git push -u origin main
git push origin v0.1.0   # optional: push initial tag
# then enable branch protection on main: require "CI gate ✓" (see docs/VERSIONING.md)
```

---
*Codename TANTU is uncleared — externals use Skopaq AI until IP-India + MCA pass. All pricing modeled pending pilot.*

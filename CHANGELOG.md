# Changelog

All notable changes to TANTU platform are documented here.  
Follows [Conventional Commits](https://www.conventionalcommits.org) + [SemVer](https://semver.org).

## v0.1.0 — 2026-08-21

### Added
- feat: initial scaffold — 5 microservices (adapter-fabric:8001, edge-perception:8002, reasoning-copilot:8003, orchestrator:8004, api-gateway:8000) + frontend:3000
- ci: ruff+mypy+pytest (matrix) + eslint/tsc/vitest + pip-audit+npm audit+gitleaks, caching
- cd: buildx per service → GHCR + GCP Artifact Registry (OIDC), semver tags
- release: conventional commits → semver → per-service VERSION → tag vX.Y.Z → changelog → SBOM (Syft) → cosign keyless sign
- docs: `docs/VERSIONING.md` + `scripts/version.sh` + `.version` single source of truth

### Security
- supply-chain: pinned deps, SBOM, cosign, gitleaks, readOnlyRootFilesystem

---

<!-- release.yml will prepend new sections above this line -->

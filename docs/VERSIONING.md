# Versioning & Release — TANTU Platform

> Single source of truth: **`.version`** at repo root (SemVer `X.Y.Z`).  
> Per-service mirrors: `services/*/VERSION`.  
> Frontend & pyproject versions are synced by `scripts/version.sh`.  
> Git tag `vX.Y.Z` is the release — CD builds & pushes images for that tag.

## Quick start

```bash
# read current version
./scripts/version.sh get          # → 0.1.0
./scripts/version.sh check        # verify all VERSION files match

# bump locally (also syncs pyproject.toml + package.json)
./scripts/version.sh bump patch   # 0.1.0 → 0.1.1
./scripts/version.sh bump minor   # 0.1.0 → 0.2.0
./scripts/version.sh bump major   # 0.1.0 → 1.0.0
./scripts/version.sh set 1.2.3    # explicit
./scripts/version.sh sync         # re-sync .version → services/*/VERSION
```

Commit & push; CI → CD → Release handle the rest. **Never hand-edit `services/*/VERSION` — use the script.**

## SemVer + Conventional Commits

We use [Conventional Commits](https://www.conventionalcommits.org) to drive automatic version bumps in `release.yml`.

| Commit prefix | Bump | Example |
|---|---|---|
| `feat!:` or `BREAKING CHANGE:` | **major** | `feat!: drop Node 18, require 20` |
| `feat:` | **minor** | `feat(adapter): add MTConnect adapter` |
| `fix:` `perf:` `refactor:` `revert:` | **patch** | `fix(gateway): handle upstream 502` |
| `docs:` `chore:` `ci:` `test:` | **none** (no release) | `docs: update ADR` |

Scopes are free-form; we use `adapter`, `edge`, `reasoning`, `orchestrator`, `gateway`, `frontend`, `infra`, `release`.

**Release workflow** (`release.yml`) on every push to `main`:

1. Reads commits since last tag `v*`.
2. Picks the highest bump (major > minor > patch).
3. Calls `scripts/version.sh set <next>` → syncs `.version`, `services/*/VERSION`, `pyproject.toml`, `frontend/package.json`.
4. Generates `CHANGELOG.md` (git-cliff / conventional-changelog / git log fallback).
5. Commits, creates annotated tag `vX.Y.Z`, pushes.
6. Generates **SBOMs** per service via **Syft** (`anchore/sbom-action`).
7. **Cosign keyless** signs SBOMs + tag (`sigstore/cosign` OIDC).
8. Creates **GitHub Release** with SBOMs + signatures attached.
9. `cd.yml` then builds & pushes images tagged `vX.Y.Z` → GHCR + GAR.

To force a bump with no feat/fix commits:

```bash
gh workflow run release.yml -f bump=minor
# or push an empty commit:
git commit --allow-empty -m "chore(release): trigger minor bump" && git push
```

## Workflows

### CI — `.github/workflows/ci.yml`

- Triggers: `push`/`pull_request` on `main`, manual dispatch.
- Jobs (with caching + matrix):
  - `python` (matrix: 5 services) → `ruff check`, `ruff format --check`, `mypy`, `pytest -q --junitxml`.
  - `frontend` → `npm ci`, `eslint`, `tsc --noEmit`, `vitest`, `next build`.
  - `pip-audit` (matrix) → `pip-audit --local` per service.
  - `npm-audit` → `npm audit`.
  - `gitleaks` → `gitleaks/gitleaks-action` SARIF → CodeQL upload.
  - `ci-gate` → aggregate; branch protection should require `CI gate ✓`.

Caching: `actions/setup-python` `cache: pip` + `actions/cache` for `~/.cache/pip`, `actions/setup-node` `cache: npm`, Next.js `.next/cache`.

### CD — `.github/workflows/cd.yml`

Builds & pushes **6 images** (matrix) via `docker/build-push-action` + `buildx` (multi-arch `linux/amd64,linux/arm64`), provenance + SBOM.

| Service | Port | Context |
|---|---|---|
| adapter-fabric | 8001 | `services/adapter-fabric` |
| edge-perception | 8002 | `services/edge-perception` |
| reasoning-copilot | 8003 | `services/reasoning-copilot` |
| orchestrator | 8004 | `services/orchestrator` |
| api-gateway | 8000 | `services/api-gateway` |
| frontend | 3000 | `frontend` |

Triggers: `push` to `main`, `tags v*.*.*`, `workflow_run: CI success`, `workflow_dispatch` (with `version` override).

Registries & tags (via `docker/metadata-action`):

- **GHCR** (always): `ghcr.io/<owner>/tantu-<service>:<semver>` + `:sha` + `:latest` (on main) + `:main`.
  Auth: `GITHUB_TOKEN` (no secret).
- **GAR** (if vars set): `<region>-docker.pkg.dev/<project>/<repo>/<service>:<semver>` (same tags).
  Auth: **OIDC Workload Identity Federation** — see GCP setup below. Cache: `type=gha` per service. Build args: `VERSION` (from `.version`/tag), `SERVICE`, `PORT`.

**Required repo variables** (Settings → Secrets and variables → Actions → Variables):

| Variable | Example | Notes |
|---|---|---|
| `GCP_PROJECT_ID` | `tantu-prod` | GCP project |
| `GCP_REGION` | `asia-south1` | GAR region (fallback `asia-south1`) |
| `GCP_GAR_REPOSITORY` | `tantu` | GAR repo name |
| `GCP_WIF_PROVIDER` | `projects/…/providers/…` | WIF provider resource name |
| `GCP_WIF_SERVICE_ACCOUNT` | `github-cd@tantu-prod.iam.gserviceaccount.com` | impersonated SA |

If GCP vars are empty, CD still pushes to GHCR and skips GAR (with a notice).

### Release — `.github/workflows/release.yml`

See flow above. Permissions: `contents: write` (commit/tag/release), `id-token: write` (cosign keyless), `packages: write`, `security-events: write`. Concurrency group `release-main` (no cancel).

Artifacts: `sbom-*.spdx.json`, signatures `*.sig`/`*.pem`, tag bundle. Attached to GitHub Release.

## Branching & Protection

- **Default branch: `main`** — all PRs target `main`; `main` is the only long-lived branch.
- **Branch protection** (configure once, Settings → Branches → Add rule for `main`):

  - ✅ Require a pull request before merging (1 approval, dismiss stale approvals, require conversation resolution).
  - ✅ Require status checks to pass before merging → check **`CI gate ✓`** (and optionally `CD gate ✓`).
  - ✅ Require branches to be up to date before merging.
  - ✅ Require signed commits (optional, recommended).
  - ✅ Do not allow bypassing the above settings (apply to admins).
  - ✅ Restrict deletions / force pushes on `main`.
  - After enabling, the API equivalent is:

    ```bash
    gh api repos/<owner>/<repo>/branches/main/protection -X PUT \
      -f required_status_checks='{"strict":true,"contexts":["CI gate ✓"]}' \
      -f enforce_admins=true \
      -f required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
      -f restrictions=null
    ```

- **Tag protection** (Settings → Tags → Add rule → `v*`): restrict who can create `v*` tags to `release.yml` bot.

## Local release dry-run

```bash
# preview next bump without tagging
gh workflow run release.yml -f bump=patch -f dry_run=true
# or locally:
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo v0.0.0)
git log "$LAST_TAG"..HEAD --oneline
./scripts/version.sh bump patch --dry-run
```

## GCP Artifact Registry + Workload Identity (OIDC) setup

No long-lived JSON keys. One-time GCP setup:

```bash
PROJECT=tantu-prod
REGION=asia-south1
REPO=tantu
SA=github-cd
POOL=github-pool
PROVIDER=github-provider
REPO_FULL=OWNER/REPO  # e.g. skopaq/tantu-platform

gcloud config set project $PROJECT
gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION

gcloud iam service-accounts create $SA --display-name="GitHub CD"

gcloud artifacts repositories add-iam-policy-binding $REPO --location=$REGION \
  --member="serviceAccount:$SA@$PROJECT.iam.gserviceaccount.com" --role="roles/artifactregistry.writer"

gcloud iam workload-identity-pools create $POOL --location=global --display-name="GitHub"
WIF_PROVIDER="projects/$(gcloud projects describe $PROJECT --format='value(projectNumber)')/locations/global/workloadIdentityPools/$POOL/providers/$PROVIDER"
gcloud iam workload-identity-pools providers create-oidc $PROVIDER --location=global \
  --workload-identity-pool=$POOL --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor" \
  --attribute-condition="assertion.repository=='$REPO_FULL'"

gcloud iam service-accounts add-iam-policy-binding $SA@$PROJECT.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WIF_PROVIDER#projects/*/locations/global/workloadIdentityPools/}/attribute.repository/$REPO_FULL"

# Then set repo variables:
gh variable set GCP_PROJECT_ID --body "$PROJECT"
gh variable set GCP_REGION --body "$REGION"
gh variable set GCP_GAR_REPOSITORY --body "$REPO"
gh variable set GCP_WIF_PROVIDER --body "$WIF_PROVIDER"
gh variable set GCP_WIF_SERVICE_ACCOUNT --body "$SA@$PROJECT.iam.gserviceaccount.com"
```

CD will now authenticate with `google-github-actions/auth` (OIDC) and push to `asia-south1-docker.pkg.dev/...`.

## Pushing for the first time

```bash
cd tantu-platform
git init -b main  # if not already a repo
git add .
git commit -m "feat: initial platform with CI/CD + versioning

- ci: ruff+mypy+pytest+npm+pip-audit+gitleaks (matrix+caching)
- cd: buildx per service → GHCR+GAR semver tags (OIDC)
- release: conventional commits → semver → tag → changelog → SBOM+cosign
"

# create GitHub repo first (gh cli or UI), then:
git remote add origin https://github.com/<OWNER>/<REPO>.git
# or SSH:
# git remote add origin git@github.com:<OWNER>/<REPO>.git

git push -u origin main

# optional: push an initial tag
git tag v0.1.0 -m "v0.1.0 — beta scaffold"
git push origin v0.1.0
```

CI runs on the push; CD builds on CI success; Release will tag the next version on the next conventional commit to `main`.

## FAQ

**Q: Do I bump version manually?**  
No — push conventional commits to `main` and `release.yml` bumps automatically. Manual `scripts/version.sh bump` is for local/offline use; commit the result and tag.

**Q: Why do `services/*/VERSION` exist if `.version` is the source?**  
So each image can `COPY VERSION` and expose `/version` without parsing git at runtime. CD passes `VERSION` as a build-arg anyway; `VERSION` files are the on-disk mirror.

**Q: SBOM & cosign — do I need keys?**  
No. Cosign uses **keyless** (Fulcio + Rekor) via OIDC (`id-token: write`). Verifiers check with `cosign verify-blob --certificate-identity-regexp ...`.

**Q: How do I cut a hotfix?**  
Branch from the tag: `git checkout -b hotfix/0.1.x v0.1.0; fix; push PR → main; release bumps patch`.

## References

- Conventional Commits 1.0.0, SemVer 2.0.0
- `python-semantic-release`, `git-cliff`, `anchore/sbom-action` (Syft), `sigstore/cosign`
- GitHub OIDC to GCP: `google-github-actions/auth` + Workload Identity Federation

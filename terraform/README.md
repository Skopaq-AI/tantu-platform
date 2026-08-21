# TANTU Platform — Terraform (GCP, Production-Grade)

GKE Autopilot + Gateway API + gradual canary (Argo Rollouts) + private data plane (Cloud SQL Postgres 16 + Timescale, Memorystore Redis, Qdrant on GKE) — region `asia-south1` (Mumbai, DPDP 2023 residency). Optimized for cost (Spot for non-prod, CUDs for prod) + autoscale (HPA + Autopilot) + minimal IAM.

## Architecture

```
                ┌─ Cloud Build trigger (GitHub → Artifact Registry) ─┐
Internet → Gateway (GKE L7 GCLB, Gateway API) → HTTPRoute → Rollout (canary 10→30→60→100% + analysis) → Service
                                                    │
                              ┌─────────────────────┼─────────────────────┐
                              │                     │                     │
                           Backend (Autopilot)  Frontend   Qdrant (Helm on GKE)
                              │                     │
                     ┌────────┼────────┐            │
                     │        │        │            │
                 Cloud SQL  Redis   Secret Manager / Artifact Registry (pull via WI)
              (PG16+Timescale (Memorystore)       GCS (tfstate)
               private IP, HA)
                              │
                    VPC (private service networking, NAT, Private Google Access)
```

**Best deployment strategy (implemented):**
- **GKE Autopilot** — no node management, auto-scale, auto-upgrade, Spot class `Scale-Out` for non-prod, `Balanced` for prod.
- **Gateway API** — `Gateway` (GKE L7 GXM) + `HTTPRoute` for L7 routing; replaces Ingress. Static global IP via TF.
- **Gradual canary via Argo Rollouts** — `Rollout` with steps `10% → pause+analysis → 30% → 60% → 80% → 100%`, auto-rollback on error-rate/p95 checks (Prometheus). Traffic split via `gatewayAPI` plugin managing `HTTPRoute` weights.
- **Image pull via Artifact Registry** — Docker repo per env, immutable tags in prod, cleanup policies, Workload Identity for pull.
- **Autoscale** — HPA (CPU 65-70%, memory) + Autopilot node autoscale; PDB for prod HA.
- **Cost-optimized** — Spot `Scale-Out` in dev/staging, on-demand in prod + CUDs (purchased out-of-band, flagged in tfvars).

## Layout

```
terraform/
  versions.tf        # TF >=1.6, google ~>5.0, GCS backend
  provider.tf        # google + google-beta, GCS bucket, enabled APIs
  variables.tf       # project_id, region (asia-south1), env, all tunables
  outputs.tf         # cluster, DB, Redis, registry, WI SAs, secrets
  main.tf            # module composition (root)
  backend.hcl        # example GCS backend config
  envs/
    dev.tfvars       # cost-optimized non-prod
    prod.tfvars      # HA prod
  modules/
    vpc/             # VPC, subnet, secondary ranges, PSA, NAT, firewall
    gke/             # Autopilot + Gateway API + static IP
    postgres/        # Cloud SQL PG16 + Timescale, private IP, HA, backup, insights
    redis/           # Memorystore Redis (private, AUTH, transit encryption)
    registry/        # Artifact Registry + cleanup policies
    iam/             # GSAs + WI bindings + minimal roles
    secrets/         # Secret Manager + rotation lifecycle
    cloudbuild/      # Cloud Build GitHub trigger
    qdrant/          # Qdrant Helm on GKE (Autopilot-compatible)
  infra/k8s/
    values.yaml      # Helm base values (Autopilot resources, HPA, Spot)
    values-dev.yaml  # dev overrides
    values-prod.yaml # prod overrides (HA, Balanced, PDB, analysis gates)
    gateway.yaml     # Gateway + HTTPRoute + HealthCheckPolicy
    rollout.yaml     # Rollout + AnalysisTemplates + Services
  cloudbuild.yaml    # CI pipeline (build → push → optional deploy)
  Makefile           # bootstrap-state, init, plan, apply wrappers
  .tflint.hcl        # google ruleset
```

## Prerequisites

- `gcloud` auth: `gcloud auth login && gcloud auth application-default login`
- `terraform` >=1.6, `kubectl`, `helm` (for post-apply k8s deploy)
- GCP project exists; you have `roles/owner` or `roles/resourcemanager.projectIamAdmin` + `roles/compute.networkAdmin` + `roles/container.admin` + `roles/cloudsql.admin`

## Bootstrap Remote State (GCS backend)

Terraform state is remote in GCS. Bucket must exist before `terraform init`.

**Option A — Makefile (recommended):**
```bash
cd terraform
# Set PROJECT_ID in envs/dev.tfvars first
make bootstrap-state ENV=dev PROJECT_ID=tantu-dev-XXXX REGION=asia-south1
# Or manually:
gsutil mb -l asia-south1 -b on --pap enforced gs://tantu-dev-XXXX-tfstate
gsutil versioning set on gs://tantu-dev-XXXX-tfstate
```

**Option B — Terraform-managed bucket (one-time):**
```bash
terraform init -backend=false
terraform apply -target=google_storage_bucket.tfstate -var-file=envs/dev.tfvars -var="create_state_bucket=true"
terraform init -backend-config="bucket=tantu-dev-XXXX-tfstate" -backend-config="prefix=tantu/dev/terraform.tfstate" -reconfigure
```

**Per-env backend config** — create `backend.dev.hcl` / `backend.prod.hcl`:
```hcl
bucket = "tantu-dev-XXXX-tfstate"
prefix = "tantu/dev/terraform.tfstate"
```

## terraform init / plan / apply

```bash
cd terraform

# Dev (Spot, zonal DB)
terraform init -backend-config="bucket=tantu-dev-XXXX-tfstate" -backend-config="prefix=tantu/dev/terraform.tfstate"
terraform workspace new dev 2>/dev/null; terraform workspace select dev
terraform plan  -var-file=envs/dev.tfvars
terraform apply -var-file=envs/dev.tfvars
# Or via Makefile:
make init ENV=dev
make plan ENV=dev
make apply ENV=dev

# Prod (HA, on-demand, deletion protection)
terraform workspace new prod 2>/dev/null; terraform workspace select prod
terraform plan  -var-file=envs/prod.tfvars
terraform apply -var-file=envs/prod.tfvars
# Makefile:
make plan ENV=prod
make apply ENV=prod
```

**Workspaces:** This config uses `terraform workspace` per env (`dev`/`prod`) — state key already prefixes by `prefix`, so workspaces are an extra isolation layer. Either is fine; keep one convention and stick to it. If you prefer TF Cloud workspaces, remove the workspace commands and use `prefix` only.

## gcloud Builder Alternative (no Terraform, for quick dev)

If you need a one-shot GCP standup without Terraform (e.g., demo or Tauranga lab):

```bash
PROJECT_ID=tantu-dev-XXXX
REGION=asia-south1
REPO=tantu

# Enable APIs
gcloud services enable compute.googleapis.com container.googleapis.com artifactregistry.googleapis.com \
  sqladmin.googleapis.com redis.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com --project $PROJECT_ID

# Artifact Registry
gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION --project=$PROJECT_ID || true

# GKE Autopilot
gcloud container clusters create-auto tantu-dev-gke --region $REGION --project $PROJECT_ID --release-channel REGULAR

# VPC + Cloud SQL + Redis (private IP via PSA — requires peering step, see terraform/modules/vpc for exact CIDR)
# For quick start, create public-IP Cloud SQL/Redis and lock with authorized networks; migrate to private via TF later.

# Build & push
gcloud builds submit --config terraform/cloudbuild.yaml --project $PROJECT_ID --substitutions=_REGION=$REGION,_REPO=$REPO,_ENV=dev

# Deploy via Helm (after setting images)
gcloud container clusters get-credentials tantu-dev-gke --region $REGION --project $PROJECT_ID
helm upgrade --install tantu ./infra/k8s/helm/tantu -n tantu --create-namespace \
  -f terraform/infra/k8s/values.yaml -f terraform/infra/k8s/values-dev.yaml \
  --set global.projectId=$PROJECT_ID
kubectl apply -f terraform/infra/k8s/gateway.yaml
kubectl apply -f terraform/infra/k8s/rollout.yaml
```

**When to use which:** `gcloud` builder = 10-min ephemeral demo; **Terraform = production source of truth** (review, drift detection, `tflint`/`tfsec`, least privilege, state locking).

## Post-Terraform: Deploy Apps to GKE

```bash
# 1. Connect
gcloud container clusters get-credentials tantu-$ENV-gke --region asia-south1 --project $PROJECT_ID

# 2. Install Argo Rollouts controller (if not Terraform-managed)
kubectl create namespace argo-rollouts --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
# Gateway API plugin (required for HTTPRoute traffic routing):
kubectl apply -n argo-rollouts -f https://raw.githubusercontent.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi/latest/install.yaml

# 3. Install Gateway + Routes
kubectl apply -f infra/k8s/gateway.yaml   # or terraform/infra/k8s/gateway.yaml
# Get LB IP:
kubectl get gateway tantu-gateway -n tantu

# 4. Deploy via Helm or Rollout manifests
helm upgrade --install tantu ./helm/tantu -n tantu --create-namespace \
  -f terraform/infra/k8s/values.yaml -f terraform/infra/k8s/values-$ENV.yaml \
  --set global.projectId=$PROJECT_ID --set backend.image.tag=$COMMIT_SHA
# Or: kubectl apply -f terraform/infra/k8s/rollout.yaml

# 5. Promote/rollback
kubectl argo rollouts get rollout tantu-backend -n tantu
kubectl argo rollouts promote tantu-backend -n tantu
kubectl argo rollouts abort tantu-backend -n tantu

# 6. Wire secrets (external-secrets operator recommended for prod)
# Example: copy from Secret Manager to k8s secret
gcloud secrets versions access latest --secret=tantu-$ENV-db-password --project=$PROJECT_ID | \
  kubectl create secret generic tantu-secrets --from-literal=DATABASE_URL="postgres://tantu_app:...@..." -n tantu --dry-run=client -o yaml | kubectl apply -f -
```

## IAM + Workload Identity

- Each KSA (`tantu/api`, `tantu/worker`, `tantu/qdrant`) has a dedicated GSA `tantu-<env>-<ns>-<ksa>` bound via `roles/iam.workloadIdentityUser`.
- No primitive roles. Workload roles: `roles/cloudsql.client`, `roles/secretmanager.secretAccessor`, `roles/artifactregistry.reader`.
- To add a new workload: add entry to `workload_identity_bindings` in `main.tf` and annotate K8s SA with `iam.gke.io/gcp-service-account: GSA_EMAIL`.

## Secret Manager

Secrets created with `ignore_changes` on `secret_data` so rotation via `gcloud secrets versions add ...` does not churn TF. Accessor grants to workload GSAs only.

```bash
echo -n "new-jwt-key" | gcloud secrets versions add tantu-dev-jwt-private-key --data-file=- --project $PROJECT_ID
```

## Cost Optimization

| Env  | GKE class | Cloud SQL | Redis | Notes |
|------|-----------|-----------|-------|-------|
| dev  | `Scale-Out` (Spot) ~60-70% discount | `db-custom-1-3840` ZONAL 20GB | `BASIC` 1GB | Auto-pause not yet; use `gcloud sql instances patch --activation-policy NEVER` off-hours |
| prod | `Balanced` (on-demand) + CUDs | `db-custom-2-7680` REGIONAL 100GB | `STANDARD_HA` 5GB | Purchase 1y/3y CUDs in Billing > Commitments |

## Hardening Checklist (tfsec / tflint)

```bash
terraform fmt -recursive
terraform validate
tflint --init && tflint
tfsec .
# Or: trivy config .
```

Enabled: private cluster, private service networking, no public DB/Redis, `require_ssl`, WI least privilege, GCS uniform access + PAP enforced, Gateway health checks, PodSecurity (non-root, readOnlyRootFS). Attach Cloud Armor to Gateway in prod (see `gateway.yaml` BackendConfig stub).

## Troubleshooting

- `Error 409: already exists` on PSA: `gcloud services vpc-peerings list --network=... --project=...` then `terraform import`.
- `Workload Identity not found`: ensure `workload_pool` matches project and KSA annotation is `GSA_EMAIL`.
- `ImagePullBackOff` from AR: grant node SA `roles/artifactregistry.reader` or use WI image pull secret; check `asia-south1-docker.pkg.dev` URL.
- `Gateway not ready`: `kubectl get gateway -n tantu -o yaml` — check `static-ips` annotation matches TF global address name.

---
*Generated for TANTU Platform — region asia-south1, Terraform google ~>5.0, GCS backend, Autopilot + Gateway API + Argo Rollouts canary.*

# Infra trigger for tantu-beta-20260821-01 2026-08-21T03:06:15Z

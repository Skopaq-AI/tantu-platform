#!/usr/bin/env bash
# Creates dedicated TANTU beta GCP project (reverts shiksha-os-dev usage)
# Usage: ./scripts/create-new-project.sh [NEW_PROJECT_ID] [REGION] [BILLING_ACCOUNT]
set -euo pipefail
NEW_PROJECT="${1:-tantu-beta-20260821-01}"
REGION="${2:-asia-south1}"
BILLING="${3:-}"

echo "=== TANTU New Project Creation (revert shiksha-os-dev) ==="
echo "New project: $NEW_PROJECT  Region: $REGION"
echo "Current gcloud account: $(gcloud config get-value account)"
echo "Current project before: $(gcloud config get-value project)"
echo ""

# 1. Create project (idempotent)
if gcloud projects describe "$NEW_PROJECT" >/dev/null 2>&1; then
  echo "Project $NEW_PROJECT already exists — reusing."
else
  echo "Creating project $NEW_PROJECT ..."
  gcloud projects create "$NEW_PROJECT" --name="TANTU Beta" --labels=project=tantu,env=beta
fi

gcloud config set project "$NEW_PROJECT"
echo "Switched to $NEW_PROJECT"

# 2. Link billing if provided or try to auto-detect
if [[ -n "$BILLING" ]]; then
  echo "Linking billing $BILLING ..."
  gcloud billing projects link "$NEW_PROJECT" --billing-account="$BILLING"
else
  echo "Skipping billing link (pass billing account as 3rd arg if needed)"
  echo "Available billing accounts:"
  gcloud billing accounts list 2>&1 | head -10 || true
fi

# 3. Enable APIs
echo "Enabling APIs ..."
gcloud services enable compute.googleapis.com container.googleapis.com servicenetworking.googleapis.com sqladmin.googleapis.com redis.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com cloudresourcemanager.googleapis.com --project "$NEW_PROJECT"

# 4. Create TF state bucket
echo "Creating TF state bucket gs://$NEW_PROJECT-tfstate ..."
gsutil mb -l "$REGION" "gs://$NEW_PROJECT-tfstate" 2>&1 | head -5 || echo "bucket exists or no perm"

# 5. Create deployer SA + WIF via helper
echo "Creating deployer SA + WIF ..."
./scripts/create-service-account.sh "$NEW_PROJECT" "$REGION" "Skopaq-AI/tantu-platform"

echo ""
echo "=== DONE ==="
echo "New project ready: $NEW_PROJECT"
echo "Verify: gcloud projects describe $NEW_PROJECT"
echo "Next: terraform apply with -var project_id=$NEW_PROJECT"
echo "Revert note: shiksha-os-dev-skopaq was NOT modified (no resources created due to sandbox proxy 403) — GH var reverted, no cloud cleanup needed. If you manually created resources there outside sandbox, delete with:"
echo "  gcloud projects delete shiksha-os-dev-skopaq  # or remove specific SA: gcloud iam service-accounts delete tantu-gha-deployer@shiksha-os-dev-skopaq.iam.gserviceaccount.com --project shiksha-os-dev-skopaq"

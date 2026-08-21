#!/usr/bin/env bash
# Creates GitHub Actions deployer SA + WIF pool/provider for TANTU on GCP.
# Works outside sandbox (needs real gcloud auth). Idempotent.
# Usage: ./scripts/create-service-account.sh [PROJECT_ID] [REGION] [GITHUB_REPO]
set -euo pipefail
PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${2:-asia-south1}"
GITHUB_REPO="${3:-Skopaq-AI/tantu-platform}"
POOL_ID="github"
PROVIDER_ID="github-provider"
SA_ID="tantu-gha-deployer"
SA_DISPLAY="TANTU GitHub Actions Deployer"

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "ERROR: PROJECT_ID required. Usage: $0 <project-id>"
  exit 1
fi

echo "=== TANTU Service Account Setup ==="
echo "Project: $PROJECT_ID  Region: $REGION  Repo: $GITHUB_REPO"
echo "Account: $(gcloud config get-value account 2>/dev/null)"
echo ""

# Extract owner/repo
OWNER="${GITHUB_REPO%%/*}"
REPO="${GITHUB_REPO##*/}"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")"
echo "Project number: $PROJECT_NUMBER"

echo ""
echo "[1/6] Enabling required APIs..."
gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com cloudresourcemanager.googleapis.com --project "$PROJECT_ID"

echo ""
echo "[2/6] Creating service account $SA_ID..."
if gcloud iam service-accounts describe "$SA_ID@$PROJECT_ID.iam.gserviceaccount.com" --project "$PROJECT_ID" >/dev/null 2>&1; then
  echo "  SA already exists: $SA_ID@$PROJECT_ID.iam.gserviceaccount.com"
else
  gcloud iam service-accounts create "$SA_ID" --project "$PROJECT_ID" --display-name="$SA_DISPLAY" --description="GitHub Actions — builds + pushes to GAR + GKE deploy + TF state"
  echo "  Created."
fi
SA_EMAIL="$SA_ID@$PROJECT_ID.iam.gserviceaccount.com"
echo "  SA email: $SA_EMAIL"

echo ""
echo "[3/6] Granting IAM roles (least-privilege + deploy)..."
for ROLE in artifactregistry.writer container.admin container.clusterAdmin iam.serviceAccountUser storage.admin cloudsql.editor secretmanager.secretAccessor secretmanager.viewer compute.viewer iam.workloadIdentityPoolAdmin; do
  echo "  + roles/$ROLE"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA_EMAIL" --role="roles/$ROLE" --condition=None >/dev/null 2>&1 ||   gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA_EMAIL" --role="roles/$ROLE" >/dev/null
done

echo ""
echo "[4/6] Creating Workload Identity Pool $POOL_ID (if needed)..."
if gcloud iam workload-identity-pools describe "$POOL_ID" --project "$PROJECT_ID" --location global >/dev/null 2>&1; then
  echo "  Pool already exists."
else
  gcloud iam workload-identity-pools create "$POOL_ID" --project "$PROJECT_ID" --location global --display-name="GitHub" --description="GitHub Actions OIDC"
  echo "  Created pool."
fi

echo ""
echo "[5/6] Creating WIF provider $PROVIDER_ID (if needed)..."
if gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" --project "$PROJECT_ID" --location global --workload-identity-pool "$POOL_ID" >/dev/null 2>&1; then
  echo "  Provider already exists."
else
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID"     --project "$PROJECT_ID" --location global --workload-identity-pool "$POOL_ID"     --issuer-uri="https://token.actions.githubusercontent.com"     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor,attribute.aud=assertion.aud,attribute.ref=assertion.ref"     --attribute-condition="assertion.repository==\"$OWNER/$REPO\""     --display-name="GitHub OIDC"
  echo "  Created provider."
fi

WIF_PROVIDER="projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID"
echo "  WIF provider: $WIF_PROVIDER"

echo ""
echo "[6/6] Binding GitHub repo to SA (workloadIdentityUser)..."
# principalSet for repo
MEMBER="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/attribute.repository/$OWNER/$REPO"
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" --project "$PROJECT_ID" --role="roles/iam.workloadIdentityUser" --member="$MEMBER" >/dev/null
echo "  Bound $MEMBER -> $SA_EMAIL"

echo ""
echo "=== DONE ==="
echo ""
echo "GitHub configuration (Settings -> Secrets and variables -> Actions):"
echo "  Secrets:"
echo "    GCP_WIP = $WIF_PROVIDER"
echo "    GCP_SA  = $SA_EMAIL"
echo "  OR (newer CD workflow vars):"
echo "    GCP_WIF_PROVIDER = $WIF_PROVIDER"
echo "    GCP_WIF_SERVICE_ACCOUNT = $SA_EMAIL"
echo "  Variables:"
echo "    GCP_PROJECT_ID = $PROJECT_ID"
echo "    GCP_REGION     = $REGION"
echo "    GCP_GAR_REPOSITORY = tantu"
echo ""
echo "Verify (outside sandbox):"
echo "  gcloud iam service-accounts describe $SA_EMAIL --project $PROJECT_ID"
echo "  gcloud iam workload-identity-pools providers describe $PROVIDER_ID --project $PROJECT_ID --location global --workload-identity-pool $POOL_ID"
echo "  gh secret set GCP_WIP --body \"$WIF_PROVIDER\" --repo $OWNER/$REPO  # requires gh auth"
echo "  gh secret set GCP_SA --body \"$SA_EMAIL\" --repo $OWNER/$REPO"
echo ""
echo "Terraform alternative (inside CI, no local gcloud needed once bootstrapped):"
echo "  terraform apply -var=\"project_id=$PROJECT_ID\" -var=\"create_state_bucket=true\"  # creates same SA+WIF via module github-deployer"

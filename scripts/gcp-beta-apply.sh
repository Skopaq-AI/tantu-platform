#!/usr/bin/env bash
set -e
PROJECT_ID=${1:-tantu-beta-$(date +%s)}
REGION=${2:-asia-south1}
ENV=${3:-dev}
echo "=== TANTU Beta GCP Apply ==="
echo "Project: $PROJECT_ID  Region: $REGION  Env: $ENV"
echo "Logged as: $(gcloud config get-value account)"
echo "Creating project $PROJECT_ID (if not exists)..."
gcloud projects create $PROJECT_ID --name="TANTU Beta" 2>&1 | head -5 || echo "project exists or no perm — using shiksha-os-dev-skopaq"
if gcloud projects describe $PROJECT_ID 2>&1 | grep -q $PROJECT_ID; then
  gcloud config set project $PROJECT_ID
else
  PROJECT_ID=$(gcloud config get-value project)
  echo "Using existing project: $PROJECT_ID"
fi
echo "Enabling APIs..."
gcloud services enable compute.googleapis.com container.googleapis.com servicenetworking.googleapis.com sqladmin.googleapis.com redis.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com --project $PROJECT_ID
echo "Creating TF state bucket..."
gsutil mb -l $REGION gs://$PROJECT_ID-tfstate 2>&1 | head -5 || echo "bucket exists"
echo "Terraform init & apply..."
cd "$(dirname "$0")/tantu-platform/terraform"
terraform init -backend-config="bucket=$PROJECT_ID-tfstate" -backend-config="prefix=env/$ENV"
terraform plan -var-file=envs/$ENV.tfvars -var="project_id=$PROJECT_ID"
terraform apply -var-file=envs/$ENV.tfvars -var="project_id=$PROJECT_ID" -auto-approve
echo "GKE auth..."
gcloud container clusters get-credentials tantu-$ENV-gke --region $REGION --project $PROJECT_ID
echo "Deploy via Helm..."
helm upgrade --install tantu ./infra/k8s -f infra/k8s/values-$ENV.yaml -n tantu --create-namespace
kubectl apply -f infra/k8s/gateway.yaml || true
echo "=== DONE ==="
echo "Gateway: https://console.cloud.google.com/kubernetes/gateway/regions/$REGION/gateways/tantu-$ENV-gateway?project=$PROJECT_ID"
echo "Logs: gcloud logging read \"resource.type=k8s_container\" --project $PROJECT_ID --limit 20"

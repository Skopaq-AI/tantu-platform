# Terraform — GCP Optimized (GKE Autopilot + Cloud Build)

## Bootstrap remote state (once)

```bash
export PROJECT_ID=tantu-dev-123456
gcloud config set project $PROJECT_ID
gsutil mb -l asia-south1 gs://$PROJECT_ID-tfstate
gcloud services enable compute.googleapis.com container.googleapis.com servicenetworking.googleapis.com sqladmin.googleapis.com redis.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com --project $PROJECT_ID
```

## Deploy

```bash
cd terraform
terraform init -backend-config="bucket=$PROJECT_ID-tfstate" -backend-config="prefix=env/dev"
terraform plan -var-file=envs/dev.tfvars -var="project_id=$PROJECT_ID"
terraform apply -var-file=envs/dev.tfvars -var="project_id=$PROJECT_ID" -auto-approve

# GKE auth + deploy
gcloud container clusters get-credentials tantu-dev-gke --region asia-south1 --project $PROJECT_ID
helm upgrade --install tantu ./infra/k8s -f infra/k8s/values-dev.yaml --namespace tantu --create-namespace
# or Argo Rollouts canary:
kubectl apply -f infra/k8s/gateway.yaml
```

## Deployment strategy (best, optimized)

- **GKE Autopilot** (pay per pod, no node mgmt, spot for dev, CUD for prod)
- **Gateway API** (GKE L7 global external managed) + **Argo Rollouts** canary (20→50→100, autoPromote 60s dev, blueGreen prod)
- **Artifact Registry** `asia-south1-docker.pkg.dev` (VPC-SC, lifecycle 30d, trivy scan in Cloud Build)
- **Cloud SQL private IP** (Timescale) + **Memorystore private** via Private Service Networking (no public IP, DPDP residency `asia-south1`)
- **Qdrant on GKE** (Helm, 1× dev 5Gi, 3× prod 20Gi premium-rwo)
- **Workload Identity** (KSA→GSA least privilege, no JSON keys)
- **Cloud Build** per-service triggers (path filter `services/adapter-fabric/**`, kaniko cache 168h)

## Cost notes

Dev ~$80/mo (Autopilot + 1× db `db-custom-2-7680` + 1GB Redis + spot) — prod ~$450/mo (HA, 3×, no spot). See `infra/k8s/values-*.yaml`.

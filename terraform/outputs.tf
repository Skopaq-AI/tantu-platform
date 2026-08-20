# TANTU Platform — Root outputs

output "project_id" {
  value       = var.project_id
  description = "GCP project ID"
}

output "region" {
  value       = var.region
  description = "Primary region"
}

output "env" {
  value       = var.env
  description = "Environment"
}

output "vpc_id" {
  value       = module.vpc.vpc_id
  description = "VPC self-link"
}

output "vpc_name" {
  value       = module.vpc.vpc_name
  description = "VPC name"
}

output "subnet_id" {
  value       = module.vpc.subnet_id
  description = "Primary subnet self-link"
}

output "gke_cluster_name" {
  value       = module.gke.cluster_name
  description = "GKE Autopilot cluster name"
}

output "gke_cluster_endpoint" {
  value       = module.gke.cluster_endpoint
  description = "GKE endpoint (sensitive)"
  sensitive   = true
}

output "gke_cluster_ca_certificate" {
  value       = module.gke.cluster_ca_certificate
  description = "GKE CA cert (sensitive)"
  sensitive   = true
}

output "artifact_registry_repo" {
  value       = module.registry.repository_url
  description = "Artifact Registry Docker repo URL (e.g. asia-south1-docker.pkg.dev/PROJECT/tantu/..)"
}

output "postgres_connection_name" {
  value       = module.postgres.connection_name
  description = "Cloud SQL connection name"
}

output "postgres_private_ip" {
  value       = module.postgres.private_ip_address
  description = "Cloud SQL private IP"
}

output "redis_host" {
  value       = module.redis.host
  description = "Memorystore Redis host"
}

output "redis_port" {
  value       = module.redis.port
  description = "Memorystore Redis port"
}

output "workload_identity_sa_emails" {
  value       = module.iam.workload_identity_sa_emails
  description = "Map of KSA -> GSA emails for Workload Identity"
}

output "secret_names" {
  value       = module.secrets.secret_ids
  description = "Created Secret Manager secret IDs"
}

output "cloudbuild_trigger_id" {
  value       = try(module.cloudbuild.trigger_id, null)
  description = "Cloud Build trigger ID (null if GitHub not configured)"
}

output "qdrant_service" {
  value       = module.qdrant.service_name
  description = "Qdrant k8s service name (in-cluster DNS)"
}

output "gateway_address" {
  value       = try(module.gke.gateway_address, null)
  description = "Gateway external IP (if provisioned)"
}

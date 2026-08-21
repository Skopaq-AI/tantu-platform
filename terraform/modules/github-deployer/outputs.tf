output "deployer_sa_email" {
  value       = google_service_account.deployer.email
  description = "GitHub deployer SA email — set as GCP_SA / GCP_WIF_SERVICE_ACCOUNT in GitHub vars"
}
output "deployer_sa_name" {
  value       = google_service_account.deployer.name
  description = "Full SA name"
}
output "wif_provider_name" {
  value       = google_iam_workload_identity_pool_provider.github.name
  description = "Full WIF provider resource name — set as GCP_WIP / GCP_WIF_PROVIDER in GitHub"
}
output "wif_pool_name" {
  value       = google_iam_workload_identity_pool.github.name
  description = "WIF pool resource name"
}
output "state_bucket_name" {
  value       = try(google_storage_bucket.tfstate[0].name, "${var.project_id}-tfstate")
  description = "TF state bucket (real if created here)"
}

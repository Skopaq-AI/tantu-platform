output "repository_name" {
  value = google_artifact_registry_repository.tantu.name
}

output "repository_id" {
  value = google_artifact_registry_repository.tantu.repository_id
}

output "repository_url" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.tantu.repository_id}"
  description = "Docker pull/push base URL"
}

output "repository_self_link" {
  value = google_artifact_registry_repository.tantu.id
}

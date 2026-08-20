output "service_name" {
  value = "qdrant"
}

output "namespace" {
  value = kubernetes_namespace.tantu.metadata[0].name
}

output "helm_release" {
  value = helm_release.qdrant.name
}

output "api_key_secret" {
  value = google_secret_manager_secret.qdrant_api_key.secret_id
}

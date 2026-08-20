output "trigger_id" {
  value = try(google_cloudbuild_trigger.github[0].trigger_id, null)
}

output "trigger_name" {
  value = try(google_cloudbuild_trigger.github[0].name, null)
}

output "logs_bucket" {
  value = try(google_storage_bucket.cloudbuild_logs[0].name, null)
}

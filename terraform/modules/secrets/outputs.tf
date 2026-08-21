output "secret_ids" {
  value = { for k, s in google_secret_manager_secret.secrets : k => s.secret_id }
}

output "secret_names" {
  value = { for k, s in google_secret_manager_secret.secrets : k => s.name }
}

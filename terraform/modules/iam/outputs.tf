output "service_accounts" {
  value       = { for k, v in google_service_account.tantu : k => v.email }
  description = "Map of KSA -> GSA emails"
}

output "workload_gsa_emails" {
  value       = { for k, v in google_service_account.tantu : k => v.email }
  description = "Alias of service_accounts for main.tf secrets accessor (map KSA -> GSA email)"
}

output "workload_identity_sa_emails" {
  value       = { for k, v in google_service_account.tantu : k => v.email }
  description = "Alias of service_accounts for root outputs (map KSA -> GSA email)"
}

output "service_accounts" { value = { for k, v in google_service_account.tantu : k => v.email } }

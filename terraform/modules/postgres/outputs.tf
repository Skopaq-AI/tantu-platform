output "instance_name" {
  value = google_sql_database_instance.postgres.name
}

output "connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "private_ip_address" {
  value = google_sql_database_instance.postgres.private_ip_address
}

output "database_name" {
  value = google_sql_database.app_db.name
}

output "db_user" {
  value = google_sql_user.app_user.name
}

output "password_secret_id" {
  value = google_secret_manager_secret.db_password.secret_id
}

output "instance_self_link" {
  value = google_sql_database_instance.postgres.self_link
}

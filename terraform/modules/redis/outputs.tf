output "id" {
  value = google_redis_instance.redis.id
}

output "host" {
  value = google_redis_instance.redis.host
}

output "port" {
  value = google_redis_instance.redis.port
}

output "auth_secret_id" {
  value = google_secret_manager_secret.redis_auth.secret_id
}

output "memory_size_gb" {
  value = google_redis_instance.redis.memory_size_gb
}

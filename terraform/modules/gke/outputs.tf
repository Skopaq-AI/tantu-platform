output "cluster_name" {
  value = google_container_cluster.autopilot.name
}

output "cluster_id" {
  value = google_container_cluster.autopilot.id
}

output "cluster_endpoint" {
  value     = google_container_cluster.autopilot.endpoint
  sensitive = true
}

output "cluster_ca_certificate" {
  value     = google_container_cluster.autopilot.master_auth[0].cluster_ca_certificate
  sensitive = true
}

output "gateway_address" {
  value       = google_compute_global_address.gateway_ip.address
  description = "Static global IP for Gateway"
}

output "gateway_ip_name" {
  value = google_compute_global_address.gateway_ip.name
}

output "workload_pool" {
  value = "${var.project_id}.svc.id.goog"
}

output "vpc_id" {
  value       = google_compute_network.vpc.id
  description = "VPC ID"
}

output "vpc_self_link" {
  value       = google_compute_network.vpc.self_link
  description = "VPC self_link (for private service networking)"
}

output "vpc_name" {
  value       = google_compute_network.vpc.name
  description = "VPC name"
}

output "subnet_id" {
  value       = google_compute_subnetwork.primary.id
  description = "Primary subnet ID"
}

output "subnet_self_link" {
  value       = google_compute_subnetwork.primary.self_link
  description = "Primary subnet self_link"
}

output "subnet_cidr" {
  value       = google_compute_subnetwork.primary.ip_cidr_range
  description = "Subnet CIDR"
}

output "private_service_range" {
  value       = try(google_compute_global_address.private_service[0].name, null)
  description = "Private service networking range name"
}

output "private_service_cidr" {
  value       = try(google_compute_global_address.private_service[0].address, null)
  description = "Private service networking base address"
}

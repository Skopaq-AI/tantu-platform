variable "project_id" { type = string }
variable "region" { type = string }
variable "env" {
  type        = string
  description = "dev | staging | prod"
}
variable "vpc_name" { type = string }
variable "cidr" {
  type        = string
  default     = "10.10.0.0/16"
  description = "VPC primary CIDR"
}
variable "subnet_cidr" {
  type        = string
  default     = null
  description = "Subnet CIDR — defaults to /20 slice of vpc cidr"
}
variable "secondary_ranges" {
  type = map(string)
  default = {
    pods     = "10.20.0.0/14"
    services = "10.24.0.0/20"
  }
  description = "Secondary ranges for GKE pods/services (required even for Autopilot for planning)"
}
variable "enable_private_service_networking" {
  type    = bool
  default = true
}
variable "private_service_cidr" {
  type        = string
  default     = "10.30.0.0/16"
  description = "CIDR for private service networking (Cloud SQL, Redis)"
}

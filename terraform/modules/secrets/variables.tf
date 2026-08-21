variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "env" {
  type = string
}

variable "secrets" {
  type = map(object({
    replication = string
  }))
  description = "Map of secret name -> config"
  default     = {}
}

variable "accessor_members" {
  type        = list(string)
  description = "Members granted secretAccessor"
  default     = []
}

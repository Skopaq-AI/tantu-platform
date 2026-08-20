variable "project_id" {type=string}
variable "region" {type=string}
variable "env" {type=string}
variable "cluster_name" {type=string}
variable "artifact_repo_name" {type=string}
variable "workload_identity_bindings" {type=map(object({roles=list(string)}))}

variable "project_id" { type=string }
variable "region" { type=string }
variable "env" { type=string }
variable "services" { type=list(string) default=["adapter-fabric","edge-perception","reasoning-copilot","orchestrator","api-gateway"] }
variable "github_owner" { type=string }
variable "github_repo" { type=string }
variable "artifact_repo" { type=string }
variable "registry_id" { type=string }

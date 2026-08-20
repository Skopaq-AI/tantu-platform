# GCS backend config — pass to terraform init via -backend-config=backend.hcl
# Copy to backend.<env>.hcl and fill per environment.
# Example: cp backend.hcl backend.dev.hcl; edit bucket/prefix

bucket = "tantu-dev-XXXX-tfstate"
prefix = "tantu/dev/terraform.tfstate"

# For prod:
# bucket = "tantu-prod-XXXX-tfstate"
# prefix = "tantu/prod/terraform.tfstate"

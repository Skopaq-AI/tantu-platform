# TANTU Terraform Makefile — thin wrappers for best-practice flow
ENV ?= dev
PROJECT_ID ?= $(shell grep project_id envs/$(ENV).tfvars | cut -d'"' -f2)
BUCKET ?= $(PROJECT_ID)-tfstate
PREFIX ?= tantu/$(ENV)/terraform.tfstate
REGION ?= asia-south1

.PHONY: bootstrap-state init plan apply destroy fmt lint sec validate clean

bootstrap-state:
	@echo ">> Creating GCS state bucket gs://$(BUCKET) in $(REGION)..."
	gsutil mb -l $(REGION) -b on --pap enforced gs://$(BUCKET) || echo "bucket exists or creation failed"
	gsutil versioning set on gs://$(BUCKET)
	@echo ">> Enable versioning done. Now run: make init ENV=$(ENV)"

init:
	terraform init \
	  -backend-config="bucket=$(BUCKET)" \
	  -backend-config="prefix=$(PREFIX)" \
	  -reconfigure
	terraform workspace select $(ENV) || terraform workspace new $(ENV)

plan:
	terraform workspace select $(ENV)
	terraform plan -var-file=envs/$(ENV).tfvars -out=tfplan-$(ENV)

apply:
	terraform workspace select $(ENV)
	terraform apply tfplan-$(ENV)

auto-apply:
	terraform workspace select $(ENV)
	terraform apply -var-file=envs/$(ENV).tfvars -auto-approve

destroy:
	terraform workspace select $(ENV)
	terraform destroy -var-file=envs/$(ENV).tfvars

fmt:
	terraform fmt -recursive

validate:
	terraform validate

lint:
	tflint --init
	tflint

sec:
	tfsec .

plan-prod:
	$(MAKE) plan ENV=prod

apply-prod:
	$(MAKE) apply ENV=prod

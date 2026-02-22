.PHONY: help install install-dev install-release-gate-core test test-quick test-all test-unit test-integration test-e2e test-security test-cov test-watch lint format codegen check-links check-placeholders check-root-layout check-docs-migration-guard check-connector-maturity check-security-baseline secret-scan env-validate smoke-workspace-wiring release-gate maturity-scorecard dev-up dev-up-full dev-down run-agent run-connector clean run-api run-web docker-build docker-up docker-down deploy-dev deploy-prod

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := black
RUFF := ruff
DOCKER_COMPOSE := docker-compose

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .

install-dev: ## Install development dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .[dev,test]
	pre-commit install

install-release-gate-core: ## Install deps required for release-gate PROFILE=core unit/integration/security scope
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .[dev,test]
	$(PIP) install slowapi cryptography sqlalchemy alembic celery email-validator

test: ## Run tests
	@$(MAKE) test-all

test-cov: ## Run tests with coverage reports
	$(PYTEST) tests/ -v --cov=agents --cov=apps --cov=packages --cov=tools --cov-report=html --cov-report=term-missing --cov-fail-under=80

test-quick: ## Run fast feedback tests (unit scope)
	@$(MAKE) test-unit

test-all: test-unit test-integration test-e2e test-security ## Run the full test taxonomy

test-unit: ## Run unit-focused tests (excludes integration, e2e, and security suites)
	$(PYTEST) tests/ -v --ignore=tests/integration --ignore=tests/e2e --ignore=tests/security

test-integration: ## Run integration tests
	$(PYTEST) tests/integration -v

test-e2e: ## Run end-to-end tests
	$(PYTEST) tests/e2e -v

test-security: ## Run security-focused tests
	$(PYTEST) tests/security -v

test-watch: ## Run tests in watch mode
	$(PYTEST) tests/ -v --looponfail

lint: ## Run linters
	$(PYTHON) -m ops.tools.lint.run

format: ## Format code with black and ruff
	$(PYTHON) -m ops.tools.format.run

codegen: ## Validate OpenAPI spec and generate summaries
	$(PYTHON) -m ops.tools.codegen.run

docs-generate: ## Generate code-derived service and connector docs
	$(PYTHON) ops/tools/codegen/generate_docs.py

check-generated-docs: ## Ensure generated documentation artifacts are up to date
	$(PYTHON) ops/tools/codegen/generate_docs.py
	git diff --exit-code -- docs/generated/services docs/connectors/generated

check-links: ## Validate internal markdown links
	$(PYTHON) ops/scripts/check-links.py

check-placeholders: ## Scan for placeholder phrases in docs and configs
	$(PYTHON) ops/scripts/check-placeholders.py

check-root-layout: ## Validate repository root allowlist
	$(PYTHON) ops/tools/check_root_layout.py


check-docs-migration-guard: ## Enforce docs legacy-to-canonical migration guard
	$(PYTHON) ops/scripts/check-docs-migration-guard.py

check-connector-maturity: ## Enforce connector maturity policy thresholds
	$(PYTHON) ops/tools/check_connector_maturity.py


check-security-baseline: ## Validate minimum production security baseline
	$(PYTHON) ops/tools/check_security_middleware.py
	$(PYTHON) ops/tools/check_secret_source_policy.py
	$(PYTEST) tests/security/test_security_baseline_compliance.py -v

secret-scan: ## Scan repository for secrets (requires gitleaks)
	gitleaks detect --source . --redact

env-validate: ## Validate service environment configuration schemas
	$(PYTHON) ops/tools/env_validate.py

smoke-workspace-wiring: ## Verify workspace methodology wiring end-to-end locally
	$(PYTHON) ops/smoke_workspace_wiring.py

release-gate: ## Run release maturity gate (PROFILE=core|full; default full)
	$(PYTHON) ops/tools/release_gate.py --profile $(if $(PROFILE),$(PROFILE),full)

maturity-scorecard: ## Consolidate maturity KPIs from CI artifacts and emit scorecards
	$(PYTHON) ops/tools/collect_maturity_score.py --artifact-root .

dev-up: ## Start the local development stack (docker-compose)
	bash ops/tools/local-dev/dev_up.sh core

dev-up-full: ## Start the complete local development stack (docker-compose)
	bash ops/tools/local-dev/dev_up.sh full

dev-down: ## Stop the local development stack (docker-compose)
	bash ops/tools/local-dev/dev_down.sh

run-agent: ## Run a single agent locally (AGENT=<agent-name> or ID=<id>)
	$(PYTHON) -m tools.agent_runner run-agent $(if $(AGENT),--name $(AGENT),) $(if $(ID),--id $(ID),)

run-connector: ## Run a connector locally (CONNECTOR=<name> and optional DRY_RUN=1)
	$(PYTHON) -m tools.connector_runner run-connector --name $(CONNECTOR) $(if $(DRY_RUN),--dry-run,)

clean: ## Clean build artifacts and cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/

run-api: ## Run the production API server
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 --app-dir apps/api-gateway/src

run-api-prod: ## Run the API server in production mode
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4 --app-dir apps/api-gateway/src

run-web: ## Run the production web console
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8501 --app-dir apps/web/src

docker-build: ## Build Docker image
	docker build -t multi-agent-ppm:latest -f apps/api-gateway/Dockerfile .

docker-build-web: ## Build web console Docker image
	docker build -t multi-agent-ppm-web:latest -f apps/web/Dockerfile apps/web

docker-up: ## Start all services with Docker Compose
	$(DOCKER_COMPOSE) up --build

docker-up-d: ## Start all services in detached mode
	$(DOCKER_COMPOSE) up --build -d

docker-down: ## Stop all Docker services
	$(DOCKER_COMPOSE) down

docker-down-v: ## Stop Docker services and remove volumes
	$(DOCKER_COMPOSE) down -v

docker-logs: ## View Docker logs
	$(DOCKER_COMPOSE) logs -f

docker-ps: ## Show running containers
	$(DOCKER_COMPOSE) ps

db-migrate: ## Run database migrations
	alembic upgrade head

db-rollback: ## Rollback last migration
	alembic downgrade -1

db-reset: ## Reset database (WARNING: destroys data)
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE) up -d db
	sleep 5
	alembic upgrade head

# Terraform commands
tf-init: ## Initialize Terraform
	cd ops/infra/terraform && terraform init

tf-plan: ## Plan Terraform changes (dev)
	cd ops/infra/terraform && terraform plan -var="environment=dev"

tf-apply: ## Apply Terraform changes (dev)
	cd ops/infra/terraform && terraform apply -var="environment=dev"

tf-destroy: ## Destroy Terraform resources (dev)
	cd ops/infra/terraform && terraform destroy -var="environment=dev"

# Kubernetes commands
k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f ops/infra/kubernetes/secrets.yaml
	kubectl apply -f ops/infra/kubernetes/deployment.yaml

k8s-status: ## Check Kubernetes deployment status
	kubectl get pods -l app=ppm-api
	kubectl get svc ppm-api-service

k8s-logs: ## View Kubernetes logs
	kubectl logs -f deployment/ppm-api

k8s-delete: ## Delete Kubernetes deployment
	kubectl delete -f ops/infra/kubernetes/deployment.yaml
	kubectl delete -f ops/infra/kubernetes/secrets.yaml

# CI/CD
ci-local: lint test check-links check-placeholders check-root-layout check-docs-migration-guard check-connector-maturity check-security-baseline ## Run CI checks locally

# Documentation
docs-serve: ## Serve documentation locally
	@echo "Documentation available at:"
	@echo "  - README: file://$(PWD)/README.md"
	@echo "  - Architecture: file://$(PWD)/docs/architecture/"
	@echo "  - Agent Specs: file://$(PWD)/agents/"

# Development helpers
env-copy: ## Copy .env.example to .env
	cp .env.example .env
	@echo "Created .env file. Please update with your values."

check: lint test check-links check-placeholders check-root-layout check-docs-migration-guard check-connector-maturity ## Run all checks (lint + test + docs scans)

all: clean install-dev lint test ## Clean, install, lint, and test

# Quick start
quick-start: env-copy install docker-up-d ## Quick start for new developers
	@echo ""
	@echo "✅ Quick start complete!"
	@echo ""
	@echo "Services running:"
	@echo "  - API: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/v1/docs"
	@echo "  - Prototype: http://localhost:8501"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your Azure credentials"
	@echo "  2. Run 'make test' to verify setup"
	@echo "  3. Visit http://localhost:8000/v1/docs to explore the API"

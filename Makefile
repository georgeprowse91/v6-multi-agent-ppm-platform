.PHONY: help install install-dev test lint format codegen dev-up dev-down run-agent run-connector clean run-api run-prototype docker-build docker-up docker-down deploy-dev deploy-prod

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := pytest
BLACK := black
RUFF := ruff
DOCKER_COMPOSE := docker-compose
STREAMLIT := streamlit

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .

install-dev: ## Install development dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .[dev]
	pre-commit install

test: ## Run tests with coverage
	$(PYTEST) tests/ -v --cov=agents --cov=apps --cov=packages --cov-report=html --cov-report=term-missing

test-quick: ## Run tests without coverage (faster)
	$(PYTEST) tests/ -v

test-watch: ## Run tests in watch mode
	$(PYTEST) tests/ -v --looponfail

lint: ## Run linters
	$(PYTHON) -m tools.lint.run

format: ## Format code with black and ruff
	$(PYTHON) -m tools.format.run

codegen: ## Validate OpenAPI spec and generate summaries
	$(PYTHON) -m tools.codegen.run

dev-up: ## Start the local development stack (docker-compose)
	bash tools/local-dev/dev_up.sh

dev-down: ## Stop the local development stack (docker-compose)
	bash tools/local-dev/dev_down.sh

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

run-prototype: ## Run the Streamlit prototype
	cd apps/web && $(STREAMLIT) run streamlit_app.py

docker-build: ## Build Docker image
	docker build -t multi-agent-ppm:latest -f apps/api-gateway/Dockerfile .

docker-build-prototype: ## Build prototype Docker image
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
	cd infra/terraform && terraform init

tf-plan: ## Plan Terraform changes (dev)
	cd infra/terraform && terraform plan -var="environment=dev"

tf-apply: ## Apply Terraform changes (dev)
	cd infra/terraform && terraform apply -var="environment=dev"

tf-destroy: ## Destroy Terraform resources (dev)
	cd infra/terraform && terraform destroy -var="environment=dev"

# Kubernetes commands
k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f infra/kubernetes/secrets.yaml
	kubectl apply -f infra/kubernetes/deployment.yaml

k8s-status: ## Check Kubernetes deployment status
	kubectl get pods -l app=ppm-api
	kubectl get svc ppm-api-service

k8s-logs: ## View Kubernetes logs
	kubectl logs -f deployment/ppm-api

k8s-delete: ## Delete Kubernetes deployment
	kubectl delete -f infra/kubernetes/deployment.yaml
	kubectl delete -f infra/kubernetes/secrets.yaml

# CI/CD
ci-local: lint test ## Run CI checks locally

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

check: lint test ## Run all checks (lint + test)

all: clean install-dev lint test ## Clean, install, lint, and test

# Quick start
quick-start: env-copy install docker-up-d ## Quick start for new developers
	@echo ""
	@echo "✅ Quick start complete!"
	@echo ""
	@echo "Services running:"
	@echo "  - API: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/api/docs"
	@echo "  - Prototype: http://localhost:8501"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your Azure credentials"
	@echo "  2. Run 'make test' to verify setup"
	@echo "  3. Visit http://localhost:8000/api/docs to explore the API"

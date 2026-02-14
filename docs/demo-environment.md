# Demo environment setup and usage

This guide explains how to provision, deploy, operate, and reset the platform demo environment.

> The demo environment is designed to **replicate full product functionality with realistic data sets and interactive tasks** so teams can run credible stakeholder walkthroughs, sales demos, onboarding sessions, and UAT rehearsals.

## Why use the demo environment

Use demo mode when you need a safe, reproducible environment that:

- Mirrors core end-to-end platform flows (API gateway, workflow orchestration, agent execution, UI dashboards).
- Starts quickly with deterministic sample payloads from `examples/demo-scenarios/`.
- Supports scripted walkthroughs without requiring production dependencies.
- Lets teams rehearse portfolio planning, approvals, lifecycle tracking, and cross-agent interactions with realistic project artifacts.

## Prerequisites

### Required tools

- Docker Engine + Docker Compose plugin
- Python `3.11+`
- `make`
- `kubectl` and `helm` (for Kubernetes deployment)
- Terraform `>= 1.5` and Azure CLI (for cloud demo infrastructure provisioning)

### Required repository setup

```bash
git clone <repo-url>
cd multi-agent-ppm-platform
cp .env.example .env
```

Then set demo mode:

```bash
# set in .env
DEMO_MODE=true
```

## Local demo quick start

The fastest local path is to start the development stack with `DEMO_MODE=true`.

```bash
make dev-up
```

Or run Docker Compose directly:

```bash
docker compose up --build
```

### Verify the stack

- API: <http://localhost:8000>
- API docs: <http://localhost:8000/v1/docs>
- Web console: <http://localhost:8501>

Run:

```bash
docker compose ps
```

## Provision the cloud demo environment (Azure + AKS)

Use this when you need a shared hosted environment for customers or internal enablement.

1. Authenticate and choose subscription:

   ```bash
   az login
   az account set --subscription "<subscription-id>"
   ```

2. Prepare Terraform variables:

   ```bash
   cd infra/terraform/envs/demo
   cp terraform.tfvars.example terraform.tfvars
   # edit terraform.tfvars values
   ```

3. Provision infrastructure:

   ```bash
   terraform init
   terraform plan -var-file=terraform.tfvars
   terraform apply -var-file=terraform.tfvars
   ```

The demo Terraform stack is tuned for cost control (single-node AKS, burstable Postgres, and LRS storage defaults).

## Deploy the demo to Kubernetes

After infrastructure exists and `kubectl` context is configured for the demo cluster:

```bash
helm upgrade --install ppm-platform-demo \
  infra/kubernetes/helm-charts/ppm-platform \
  --namespace ppm-demo \
  --create-namespace \
  -f infra/kubernetes/helm-charts/ppm-platform/demo-values.yaml
```

Verify deployment health:

```bash
kubectl get pods -n ppm-demo
kubectl get svc -n ppm-demo
```

## Load dummy data and demo assets

The repository ships curated demo payloads in `examples/demo-scenarios/`.

### Option A: UI/API demo mode

Set `DEMO_MODE=true` and start the stack. In demo mode, dashboard and scenario views consume static example payloads (for example portfolio health and lifecycle metrics) so the experience is immediately usable.

### Option B: Run scripted payload flows

Use the smoke script to execute deterministic demo interactions against workflow + API applications:

```bash
python ops/scripts/quickstart_smoke.py
```

This script uses `examples/demo-scenarios/quickstart-*.json` payloads and mock LLM responses for repeatable runs.

## Run scripted scenarios

Use scenario artifacts for walkthroughs, regression demos, and training:

1. Inspect available scenario files:

   ```bash
   ls examples/demo-scenarios
   ```

2. Start demo stack (`DEMO_MODE=true`) and execute script-driven flow:

   ```bash
   python ops/scripts/quickstart_smoke.py
   ```

3. Drive UI walkthroughs using the demo dashboard route:

   ```text
   /workspace?project_id=demo-1
   ```

Recommended scripted flow order:

1. Intake/query submission
2. Workflow initiation and monitoring
3. Approvals and stage-gate progression
4. Portfolio health and lifecycle review


## Before every client demo

Use this quick checklist right before each customer-facing session:

1. Reset the environment state and clear caches.
2. Regenerate demo data (`./scripts/reset_demo_data.sh --regenerate --size <N> --seed <S>`).
3. Load regenerated data into configured stores.
4. Run a smoke check (`python ops/scripts/quickstart_smoke.py`).
5. Open key demo URLs (API docs, web console, and scenario route) to verify readiness.

## Reset the demo environment

### Reset local containers and volumes

```bash
docker compose down -v
docker compose up --build
```

Or with Make targets:

```bash
make dev-down
make dev-up
```

### Reset database state

```bash
make db-reset
```

> `db-reset` destroys local DB state and recreates migrations; use only for disposable demo data.

### Reset and regenerate with helper script

Use `scripts/reset_demo_data.sh` to run a full refresh workflow: stop app services, recreate the PostgreSQL demo database, clear Redis cache, run migrations, reload demo JSON/CSV assets, and start services again.

```bash
./scripts/reset_demo_data.sh
```

To generate a fresh dataset before loading, pass `--regenerate` (optionally with generator args):

```bash
./scripts/reset_demo_data.sh --regenerate --size 5 --seed 123
```

The regeneration step uses `scripts/generate_demo_data.py`, which can also be run standalone to rewrite the canonical demo files under `data/demo/*.json` and the `data/seed/manifest.csv` summary.

```bash
python scripts/generate_demo_data.py --size 4 --seed 77
```

> `generate_demo_data.py` uses Faker when available and otherwise falls back to built-in pseudo-random generators, while preserving canonical entity shapes expected by `scripts/load_demo_data.py`.

### Reset cloud demo deployment

- Reapply Helm release to restore desired state:

  ```bash
  helm upgrade --install ppm-platform-demo \
    infra/kubernetes/helm-charts/ppm-platform \
    --namespace ppm-demo \
    -f infra/kubernetes/helm-charts/ppm-platform/demo-values.yaml
  ```

- If full rebuild is required, destroy and reprovision with Terraform in `infra/terraform/envs/demo`.

## Demo mode vs production mode

### Purpose of demo mode

Demo mode exists to provide a stable, low-risk environment that showcases the platform's end-to-end capabilities with realistic data and interactive workflows, while minimizing setup complexity and operating cost.

### Demo mode characteristics

- Deterministic sample data and mockable upstream dependencies.
- Faster startup and lower infrastructure sizing.
- Reduced operational overhead for rehearsals and enablement.

### Limitations compared with production

- Not a substitute for production-grade security hardening, secrets management, and compliance controls.
- May use static JSON and mocked responses instead of live enterprise systems.
- Performance, scale, and HA settings are intentionally reduced.
- Operational telemetry and SLO behavior can differ from production traffic patterns.

For production deployments, use environment-specific secrets, full observability baselines, hardened networking policies, and real connector integrations.

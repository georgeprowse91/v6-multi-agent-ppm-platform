# Docker Compose Profiles Runbook

## Purpose

This runbook documents deterministic local stack startup using Compose profiles:

- `demo`: smallest UX-centric stack for product demos.
- `core`: core platform stack for local development.
- `full`: all first-class app/service processes currently implemented in `apps/*/src/main.py` and `services/*/src/main.py`.

## Profile startup order

Compose enforces health-gated `depends_on` links. The effective startup sequence is:

1. `db`, `redis`
2. foundational APIs: `workflow-service`, `identity-access`, `data-service`
3. domain/core APIs: `api`, `orchestration-service`, `policy-engine`, `document-service`, `audit-log`, `notification-service`
4. extended/full APIs (full profile): `analytics-service`, `data-lineage-service`, `data-sync-service`, `telemetry-service`, `agent-runtime`, `auth-service`, `realtime-coedit-service`
5. `web`

## Services and ports by profile

### demo profile

| Service | Host port | Container port | Health endpoint |
|---|---:|---:|---|
| api | 8000 | 8000 | `/healthz` |
| workflow-service | 8080 | 8080 | `/healthz` |
| web | 8501 | 8501 | `/healthz` |
| db | 5432 | 5432 | `pg_isready` |
| redis | 6379 | 6379 | `redis-cli ping` |

### core profile

Includes all `demo` services, plus:

| Service | Host port | Container port | Health endpoint |
|---|---:|---:|---|
| identity-access | 8081 | 8080 | `/healthz` |
| data-service | 8082 | 8080 | `/healthz` |
| policy-engine | 8083 | 8080 | `/healthz` |
| notification-service | 8084 | 8080 | `/healthz` |
| audit-log | 8085 | 8080 | `/healthz` |
| orchestration-service | 8087 | 8080 | `/healthz` |
| document-service | 8088 | 8080 | `/healthz` |

### full profile

Includes all `core` services, plus:

| Service | Host port | Container port | Health endpoint |
|---|---:|---:|---|
| analytics-service | 8086 | 8080 | `/healthz` |
| data-lineage-service | 8089 | 8080 | `/healthz` |
| data-sync-service | 8090 | 8080 | `/healthz` |
| telemetry-service | 8091 | 8080 | `/healthz` |
| agent-runtime | 8092 | 8080 | `/healthz` |
| auth-service | 8093 | 8080 | `/healthz` |
| realtime-coedit-service | 8094 | 8080 | `/healthz` |

## Startup commands

```bash
# demo stack
COMPOSE_PROFILES=demo docker-compose --profile demo up --build -d

# core stack (default dev target)
make dev-up

# full stack
make dev-up-full
```

## Readiness validation

### Compose-level health

```bash
docker-compose ps
```

```bash
docker-compose ps --format json | jq -r '. | "\(.Name)\t\(.State)\t\(.Health)"'
```

### HTTP health checks

```bash
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8080/healthz
curl -fsS http://localhost:8501/healthz
```

Core additions:

```bash
curl -fsS http://localhost:8081/healthz
curl -fsS http://localhost:8082/healthz
curl -fsS http://localhost:8083/healthz
curl -fsS http://localhost:8084/healthz
curl -fsS http://localhost:8085/healthz
curl -fsS http://localhost:8087/healthz
curl -fsS http://localhost:8088/healthz
```

Full additions:

```bash
curl -fsS http://localhost:8086/healthz
curl -fsS http://localhost:8089/healthz
curl -fsS http://localhost:8090/healthz
curl -fsS http://localhost:8091/healthz
curl -fsS http://localhost:8092/healthz
curl -fsS http://localhost:8093/healthz
curl -fsS http://localhost:8094/healthz
```

## Shutdown

```bash
make dev-down
```

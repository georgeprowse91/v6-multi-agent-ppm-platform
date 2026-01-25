# Local Development Stack

Use the scripts in this folder to start and stop the local Docker Compose stack
defined in the repo root (`docker-compose.yml`).

## Quick start

```bash
bash tools/local-dev/dev_up.sh
```

This brings up:
* API gateway (`api`) on `http://localhost:8000`
* PostgreSQL on `localhost:5432`
* Redis on `localhost:6379`
* Streamlit prototype (`web`) on `http://localhost:8501`

## How to verify

```bash
curl http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok","timestamp":"2024-01-01T12:00:00","version":"0.1.0"}
```

## Stop the stack

```bash
bash tools/local-dev/dev_down.sh
```

## Environment configuration

Copy `.env.example` to `.env` and set your Azure credentials before running the stack:

```bash
cp .env.example .env
```

## Optional overrides

The file `docker-compose.override.example.yml` shows how to add extra environment
variables or bind-mounts locally. Copy it to the repo root as
`docker-compose.override.yml` to apply the changes.

## Key files

- `tools/local-dev/dev_up.sh`: starts Docker Compose with safety checks.
- `tools/local-dev/dev_down.sh`: stops Docker Compose.
- `docker-compose.yml`: core service definitions.

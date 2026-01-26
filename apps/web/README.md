# Production Web Console

Production-grade web console for the Multi-Agent PPM platform. The UI authenticates via OIDC, stores
server-side sessions, and calls downstream services with tenant-aware headers.

## Quickstart

```bash
cd apps/web
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8501
```

Open the UI at `http://localhost:8501`.

## Features

- OIDC login + server-side session management.
- Tenant-aware calls to `api-gateway` and `workflow-engine`.
- Workflow start action via `workflow-engine`.

## Configuration

Environment variables:

- `API_GATEWAY_URL` (default: `http://localhost:8000`)
- `WORKFLOW_ENGINE_URL` (default: `http://localhost:8082`)
- `OIDC_CLIENT_ID` (required)
- `OIDC_CLIENT_SECRET` (required for confidential clients)
- `OIDC_AUTH_URL` (required)
- `OIDC_TOKEN_URL` (required)
- `OIDC_REDIRECT_URI` (required)
- `OIDC_JWKS_URL` (required unless `OIDC_INSECURE_SKIP_VERIFY=true`)
- `OIDC_ISSUER` (optional)
- `OIDC_AUDIENCE` (optional)
- `OIDC_LOGOUT_URL` (optional)
- `OIDC_SCOPE` (default: `openid profile email`)
- `OIDC_TENANT_CLAIM` (default: `tenant_id`)

## Key files

- `apps/web/src/main.py`: FastAPI app serving static UI.
- `apps/web/static/`: HTML/CSS/JS assets.

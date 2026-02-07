from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


async def _run() -> None:
    examples = REPO_ROOT / "examples" / "demo-scenarios"
    request_payload = _load_json(examples / "quickstart-request.json")
    workflow_payload = _load_json(examples / "quickstart-workflow.json")

    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("AUTH_DEV_MODE", "true")
    os.environ.setdefault("AUTH_DEV_ROLES", "tenant_owner")
    os.environ.setdefault("AUTH_DEV_TENANT_ID", "dev-tenant")
    os.environ.setdefault("LLM_PROVIDER", "mock")
    os.environ.setdefault(
        "LLM_MOCK_RESPONSE_PATH", str(examples / "quickstart-llm-response.json")
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["WORKFLOW_DB_PATH"] = str(Path(tmpdir) / "workflows.db")

        api_root = REPO_ROOT / "apps" / "api-gateway" / "src"
        workflow_root = REPO_ROOT / "apps" / "workflow-engine" / "src"
        for root in (api_root, workflow_root, REPO_ROOT):
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))

        from api.main import app as api_app  # noqa: WPS433
        from main import app as workflow_app  # noqa: WPS433

        async with httpx.AsyncClient(app=workflow_app, base_url="http://workflow") as wf_client:
            wf_response = await wf_client.post(
                "/workflows/start",
                headers={"X-Tenant-ID": "dev-tenant"},
                json=workflow_payload,
            )
            wf_response.raise_for_status()

        async with httpx.AsyncClient(app=api_app, base_url="http://api") as api_client:
            api_response = await api_client.post(
                "/v1/query",
                headers={"X-Tenant-ID": "dev-tenant"},
                json=request_payload,
            )
            api_response.raise_for_status()
            data = api_response.json()

        assert data["success"] is True, data
        summary = data["data"]["execution_summary"]
        assert summary["total_agents"] == 3, data
        assert summary["successful"] == 3, data


if __name__ == "__main__":
    asyncio.run(_run())

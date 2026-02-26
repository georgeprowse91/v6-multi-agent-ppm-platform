from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

DEMO_SCENARIOS_DIR = REPO_ROOT / "examples" / "demo-scenarios"
DEMO_LOG_PATH = REPO_ROOT / "data" / "demo" / "demo_run_log.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _prepare_environment() -> None:
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("AUTH_DEV_MODE", "true")
    os.environ.setdefault("AUTH_DEV_ROLES", "tenant_owner")
    os.environ.setdefault("AUTH_DEV_TENANT_ID", "dev-tenant")
    os.environ.setdefault("LLM_PROVIDER", "mock")
    os.environ.setdefault(
        "LLM_MOCK_RESPONSE_PATH",
        str(DEMO_SCENARIOS_DIR / "full-platform-llm-response.json"),
    )


def _build_demo_log(
    *,
    workflow_response: dict,
    api_response: dict,
    request_payload: dict,
) -> dict:
    agent_results = api_response["data"].get("agent_results", [])
    return {
        "run_id": workflow_response["run_id"],
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "total_agents": 25,
        "agents": [
            {
                "agent_id": agent["agent_id"],
                "status": "completed" if agent.get("success") else "failed",
            }
            for agent in agent_results
        ],
        "correlation_id": request_payload.get("context", {}).get("correlation_id")
        or workflow_response.get("run_id")
        or str(uuid4()),
    }


def _write_demo_log(payload: dict) -> None:
    DEMO_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEMO_LOG_PATH.write_text(f"{json.dumps(payload, indent=2)}\n")


async def run_full_platform_demo() -> dict:
    _prepare_environment()

    request_payload = _load_json(DEMO_SCENARIOS_DIR / "full-platform-request.json")
    workflow_payload = _load_json(DEMO_SCENARIOS_DIR / "full-platform-workflow.json")

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["WORKFLOW_DB_PATH"] = str(Path(tmpdir) / "workflows.db")

        from api.main import app as api_app  # noqa: WPS433
        from main import app as workflow_app  # noqa: WPS433

        async with httpx.AsyncClient(app=workflow_app, base_url="http://workflow") as wf_client:
            wf_response = await wf_client.post(
                "/workflows/start",
                headers={"X-Tenant-ID": "dev-tenant"},
                json=workflow_payload,
            )
            wf_response.raise_for_status()
            workflow_data = wf_response.json()

        async with httpx.AsyncClient(app=api_app, base_url="http://api") as api_client:
            query_response = await api_client.post(
                "/v1/query",
                headers={"X-Tenant-ID": "dev-tenant"},
                json=request_payload,
            )
            query_response.raise_for_status()
            query_data = query_response.json()

    assert query_data["success"] is True, query_data
    summary = query_data["data"]["execution_summary"]
    assert summary["total_agents"] == 25, query_data
    assert summary["successful"] == 25, query_data

    demo_log = _build_demo_log(
        workflow_response=workflow_data,
        api_response=query_data,
        request_payload=request_payload,
    )
    _write_demo_log(demo_log)
    return demo_log


if __name__ == "__main__":
    asyncio.run(run_full_platform_demo())

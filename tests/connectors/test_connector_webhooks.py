from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONNECTORS_ROOT = REPO_ROOT / "integrations" / "connectors"


WEBHOOK_CASES: list[tuple[str, Path]] = [
    ("planview", CONNECTORS_ROOT / "planview" / "src" / "webhooks.py"),
    ("clarity", CONNECTORS_ROOT / "clarity" / "src" / "webhooks.py"),
    ("ms_project_server", CONNECTORS_ROOT / "ms_project_server" / "src" / "webhooks.py"),
    ("jira", CONNECTORS_ROOT / "jira" / "src" / "webhooks.py"),
    ("azure_devops", CONNECTORS_ROOT / "azure_devops" / "src" / "webhooks.py"),
    ("monday", CONNECTORS_ROOT / "monday" / "src" / "webhooks.py"),
    ("asana", CONNECTORS_ROOT / "asana" / "src" / "webhooks.py"),
    ("sharepoint", CONNECTORS_ROOT / "sharepoint" / "src" / "webhooks.py"),
    ("confluence", CONNECTORS_ROOT / "confluence" / "src" / "webhooks.py"),
    ("google_drive", CONNECTORS_ROOT / "google_drive" / "src" / "webhooks.py"),
    ("sap", CONNECTORS_ROOT / "sap" / "src" / "webhooks.py"),
    ("oracle", CONNECTORS_ROOT / "oracle" / "src" / "webhooks.py"),
    ("netsuite", CONNECTORS_ROOT / "netsuite" / "src" / "webhooks.py"),
    ("workday", CONNECTORS_ROOT / "workday" / "src" / "webhooks.py"),
    ("sap_successfactors", CONNECTORS_ROOT / "sap_successfactors" / "src" / "webhooks.py"),
    ("adp", CONNECTORS_ROOT / "adp" / "src" / "webhooks.py"),
    ("teams", CONNECTORS_ROOT / "teams" / "src" / "webhooks.py"),
    ("slack", CONNECTORS_ROOT / "slack" / "src" / "webhooks.py"),
    ("smartsheet", CONNECTORS_ROOT / "smartsheet" / "src" / "webhooks.py"),
    ("outlook", CONNECTORS_ROOT / "outlook" / "src" / "webhooks.py"),
    ("google_calendar", CONNECTORS_ROOT / "google_calendar" / "src" / "webhooks.py"),
    (
        "azure_communication_services",
        CONNECTORS_ROOT / "azure_communication_services" / "src" / "webhooks.py",
    ),
    ("twilio", CONNECTORS_ROOT / "twilio" / "src" / "webhooks.py"),
    ("notification_hubs", CONNECTORS_ROOT / "notification_hubs" / "src" / "webhooks.py"),
    ("zoom", CONNECTORS_ROOT / "zoom" / "src" / "webhooks.py"),
    ("servicenow", CONNECTORS_ROOT / "servicenow" / "src" / "webhooks.py"),
    ("archer", CONNECTORS_ROOT / "archer" / "src" / "webhooks.py"),
    ("logicgate", CONNECTORS_ROOT / "logicgate" / "src" / "webhooks.py"),
]


def _load_module(path: Path, connector_id: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"webhooks_{connector_id}", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to load webhook module for {connector_id}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("connector_id,path", WEBHOOK_CASES)
def test_webhook_handlers_present(connector_id: str, path: Path) -> None:
    module = _load_module(path, connector_id)
    assert hasattr(module, "handle_webhook")
    assert hasattr(module, "register_webhook")


@pytest.mark.parametrize("connector_id,path", WEBHOOK_CASES)
def test_webhook_handlers_response(connector_id: str, path: Path) -> None:
    module = _load_module(path, connector_id)
    payload = {"event_type": "updated", "resource": {"id": "1"}}
    headers = {"x-event-type": "updated"}
    handled = module.handle_webhook(payload, headers)
    assert isinstance(handled, dict)
    assert handled.get("connector_id")

    registered = module.register_webhook("https://example.com/webhook", "secret")
    assert registered["status"] == "registered"
    assert registered["webhook_url"] == "https://example.com/webhook"

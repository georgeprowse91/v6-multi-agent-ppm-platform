from pathlib import Path

import pytest

CONNECTOR_DIRS = [
    "azure_devops",
    "jira",
    "planview",
    "salesforce",
    "sap",
    "servicenow",
    "sharepoint",
    "slack",
    "teams",
    "workday",
]


@pytest.mark.parametrize("connector", CONNECTOR_DIRS)
def test_connector_runtime_maps_fixture(connector: str) -> None:
    connector_root = Path(__file__).resolve().parents[2] / connector
    fixture_path = connector_root / "tests" / "fixtures" / "projects.json"
    module_path = connector_root / "src" / "main.py"
    assert fixture_path.exists()

    namespace: dict[str, object] = {}
    exec(module_path.read_text(), namespace)
    run_sync = namespace["run_sync"]
    results = run_sync(fixture_path, "tenant-test")

    assert results
    record = results[0]
    assert record["tenant_id"] == "tenant-test"
    assert record["id"] == "proj-100"
    assert record["name"] == "Migration Wave 1"

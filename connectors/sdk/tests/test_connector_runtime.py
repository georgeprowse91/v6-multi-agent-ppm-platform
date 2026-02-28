import importlib.util
from pathlib import Path
from types import ModuleType

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


def _ensure_path_within(path: Path, parent: Path, description: str) -> Path:
    resolved_path = path.resolve()
    resolved_parent = parent.resolve()
    try:
        resolved_path.relative_to(resolved_parent)
    except ValueError as exc:
        raise ValueError(f"{description} must be within {resolved_parent}") from exc
    return resolved_path


def _load_connector_module(module_path: Path, connector_root: Path) -> ModuleType:
    if module_path.suffix != ".py":
        raise ValueError("connector module must be a Python file")

    _ensure_path_within(module_path, connector_root / "src", "connector module path")

    spec = importlib.util.spec_from_file_location(f"connector_{connector_root.name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load connector module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "run_sync"):
        raise AttributeError("connector module must define run_sync")
    if not callable(module.run_sync):
        raise TypeError("connector module run_sync must be callable")

    return module


@pytest.mark.parametrize("connector", CONNECTOR_DIRS)
def test_connector_runtime_maps_fixture(connector: str) -> None:
    connector_root = Path(__file__).resolve().parents[2] / connector
    fixture_path = connector_root / "tests" / "fixtures" / "projects.json"
    module_path = connector_root / "src" / "main.py"
    assert fixture_path.suffix == ".json"
    fixture_path = _ensure_path_within(
        fixture_path,
        connector_root / "tests" / "fixtures",
        "fixture path",
    )
    assert fixture_path.exists()

    module = _load_connector_module(module_path, connector_root)
    results = module.run_sync(fixture_path, "tenant-test")

    assert results
    record = results[0]
    assert record["tenant_id"] == "tenant-test"
    assert record["id"] == "proj-100"
    assert record["name"] == "Migration Wave 1"


def test_connector_runtime_rejects_unauthorized_module_path(tmp_path: Path) -> None:
    module_path = tmp_path / "malicious.py"
    module_path.write_text("def run_sync(*_args):\n    return []\n")

    connector_root = Path(__file__).resolve().parents[2] / "jira"
    with pytest.raises(ValueError, match="connector module path"):
        _load_connector_module(module_path, connector_root)

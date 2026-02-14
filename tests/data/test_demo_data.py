from __future__ import annotations

import json
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "data" / "demo"
SCHEMA_DIR = REPO_ROOT / "data" / "schemas"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _ids(rows: list[dict], key: str = "id") -> set[str]:
    return {str(r[key]) for r in rows}


def test_demo_files_present() -> None:
    expected = {
        "portfolios.json",
        "programs.json",
        "projects.json",
        "tasks.json",
        "resources.json",
        "budgets.json",
        "epics.json",
        "sprints.json",
        "risks.json",
        "issues.json",
        "vendors.json",
        "contracts.json",
        "policies.json",
        "approvals.json",
    }
    assert expected.issubset({p.name for p in DEMO_DIR.glob("*.json")})


def test_demo_data_matches_canonical_schemas() -> None:
    schema_map = {
        "portfolios": "portfolio.schema.json",
        "programs": "program.schema.json",
        "projects": "project.schema.json",
        "tasks": "work-item.schema.json",
        "resources": "resource.schema.json",
        "budgets": "budget.schema.json",
        "risks": "risk.schema.json",
        "issues": "issue.schema.json",
        "vendors": "vendor.schema.json",
    }

    for entity_name, schema_name in schema_map.items():
        schema = _read_json(SCHEMA_DIR / schema_name)
        rows = _read_json(DEMO_DIR / f"{entity_name}.json")
        for row in rows:
            jsonschema.validate(row, schema)


def test_demo_relationship_integrity() -> None:
    portfolios = _read_json(DEMO_DIR / "portfolios.json")
    programs = _read_json(DEMO_DIR / "programs.json")
    projects = _read_json(DEMO_DIR / "projects.json")
    tasks = _read_json(DEMO_DIR / "tasks.json")
    resources = _read_json(DEMO_DIR / "resources.json")
    budgets = _read_json(DEMO_DIR / "budgets.json")
    risks = _read_json(DEMO_DIR / "risks.json")
    issues = _read_json(DEMO_DIR / "issues.json")
    vendors = _read_json(DEMO_DIR / "vendors.json")
    contracts = _read_json(DEMO_DIR / "contracts.json")
    approvals = _read_json(DEMO_DIR / "approvals.json")
    epics = _read_json(DEMO_DIR / "epics.json")
    sprints = _read_json(DEMO_DIR / "sprints.json")

    portfolio_ids = _ids(portfolios)
    program_ids = _ids(programs)
    project_ids = _ids(projects)
    resource_ids = _ids(resources)
    budget_ids = _ids(budgets)
    vendor_ids = _ids(vendors)
    contract_ids = _ids(contracts)

    assert all(program["portfolio_id"] in portfolio_ids for program in programs)
    assert all(project["program_id"] in program_ids for project in projects)
    assert all(task["project_id"] in project_ids for task in tasks)
    assert all(task["assigned_to"] in resource_ids for task in tasks)
    assert all(budget["portfolio_id"] in portfolio_ids for budget in budgets)
    assert all(risk["project_id"] in project_ids for risk in risks)
    assert all(issue["project_id"] in project_ids for issue in issues)
    assert all(epic["project_id"] in project_ids for epic in epics)
    assert all(sprint["project_id"] in project_ids for sprint in sprints)
    assert all(contract["vendor_id"] in vendor_ids for contract in contracts)
    assert all(contract["project_id"] in project_ids for contract in contracts)

    approval_targets = {
        ("budget", budget_id) for budget_id in budget_ids
    } | {
        ("contract", contract_id) for contract_id in contract_ids
    }
    assert all((approval["entity_type"], approval["entity_id"]) in approval_targets for approval in approvals)


def test_demo_minimum_record_counts() -> None:
    projects = _read_json(DEMO_DIR / "projects.json")
    tasks = _read_json(DEMO_DIR / "tasks.json")
    risks = _read_json(DEMO_DIR / "risks.json")
    issues = _read_json(DEMO_DIR / "issues.json")

    assert len(projects) >= 10
    assert len(tasks) >= 100
    assert len(risks) >= 30
    assert len(issues) >= 30

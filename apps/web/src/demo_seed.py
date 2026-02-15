from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from knowledge_store import KnowledgeStore
from methodologies import get_methodology_map
from security.audit_log import build_event, get_audit_log_store
from spreadsheet_models import ColumnCreate, RowCreate, SheetCreate
from spreadsheet_store import SpreadsheetStore
from timeline_models import MilestoneCreate
from timeline_store import TimelineStore
from tree_models import NodeType, TreeNodeCreate, TreeNodeRef
from tree_store import TreeStore
from workspace_state_store import WorkspaceStateStore

if False:
    from demo_integrations import DemoOutbox

DEMO_TENANT_ID = "demo-tenant"
DEMO_PORTFOLIO_ID = "demo-portfolio"
DEMO_PROGRAM_ID = "demo-program"
DEMO_PROJECTS: dict[str, str] = {
    "demo-predictive": "predictive",
    "demo-adaptive": "adaptive",
    "demo-hybrid": "hybrid",
}


def _load_seed_fixture() -> dict[str, Any]:
    fixture_path = Path(__file__).resolve().parent.parent / "data" / "demo_seed.json"
    try:
        with fixture_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _seed_workspace_state(workspace_state_store: WorkspaceStateStore, project_id: str, methodology: str) -> None:
    methodology_map = get_methodology_map(methodology)
    stages = methodology_map.get("stages", [])
    first_stage = stages[0] if stages else {}
    first_activity = (first_stage.get("activities") or [{}])[0]

    completion: dict[str, bool] = {}
    all_activities: list[dict[str, Any]] = []
    for stage in stages:
        all_activities.extend(stage.get("activities", []))
    all_activities.extend(methodology_map.get("monitoring", []))

    selected_index = max(0, len(all_activities) // 2)
    selected_activity = all_activities[selected_index] if all_activities else first_activity

    for index, activity in enumerate(all_activities):
        activity_id = activity.get("id")
        if not activity_id:
            continue
        if methodology == "predictive":
            completion[activity_id] = index % 4 in {0, 1}
        elif methodology == "adaptive":
            completion[activity_id] = index % 3 == 0
        else:
            completion[activity_id] = index % 5 in {0, 1, 3}

    workspace_state_store.update_selection(
        DEMO_TENANT_ID,
        project_id,
        {
            "methodology": methodology,
            "current_stage_id": first_stage.get("id"),
            "current_activity_id": selected_activity.get("id"),
            "activity_completion": completion,
            "current_canvas_tab": "document",
        },
    )


def _seed_sheet(spreadsheet_store: SpreadsheetStore, project_id: str) -> str:
    existing = spreadsheet_store.list_sheets(DEMO_TENANT_ID, project_id)
    if existing:
        return existing[0].sheet_id

    sheet = spreadsheet_store.create_sheet(
        DEMO_TENANT_ID,
        project_id,
        SheetCreate(
            name="RAID Register",
            columns=[
                ColumnCreate(name="Type", type="text", required=True),
                ColumnCreate(name="Title", type="text", required=True),
                ColumnCreate(name="Owner", type="text", required=True),
                ColumnCreate(name="Status", type="text", required=True),
            ],
        ),
    )
    column_ids = {column.name: column.column_id for column in sheet.columns}
    spreadsheet_store.add_row(
        DEMO_TENANT_ID,
        project_id,
        sheet.sheet_id,
        RowCreate(
            values={
                column_ids["Type"]: "Risk",
                column_ids["Title"]: "Vendor delivery dependency",
                column_ids["Owner"]: "PMO",
                column_ids["Status"]: "Mitigating",
            }
        ),
    )
    return sheet.sheet_id


def _seed_timeline(timeline_store: TimelineStore, project_id: str) -> str:
    milestones = timeline_store.list_milestones(DEMO_TENANT_ID, project_id)
    if milestones:
        return milestones[0].milestone_id
    milestone = timeline_store.create_milestone(
        DEMO_TENANT_ID,
        project_id,
        MilestoneCreate(title="Gate Review", date="2026-03-15", status="planned", owner="PMO"),
    )
    return milestone.milestone_id


def _seed_tree_artifacts(tree_store: TreeStore, project_id: str, sheet_id: str, milestone_id: str) -> None:
    nodes = tree_store.list_nodes(DEMO_TENANT_ID, project_id)
    if nodes:
        return
    root = tree_store.create_node(
        DEMO_TENANT_ID,
        project_id,
        TreeNodeCreate(type=NodeType.folder, title="Seeded Artifacts", parent_id=None),
    )
    tree_store.create_node(
        DEMO_TENANT_ID,
        project_id,
        TreeNodeCreate(
            type=NodeType.document,
            parent_id=root.node_id,
            title="Business Case",
            ref=TreeNodeRef(document_id=f"{project_id}-business-case"),
        ),
    )
    tree_store.create_node(
        DEMO_TENANT_ID,
        project_id,
        TreeNodeCreate(
            type=NodeType.sheet,
            parent_id=root.node_id,
            title="RAID Register",
            ref=TreeNodeRef(sheet_id=sheet_id),
        ),
    )
    tree_store.create_node(
        DEMO_TENANT_ID,
        project_id,
        TreeNodeCreate(
            type=NodeType.milestone,
            parent_id=root.node_id,
            title="Milestones",
            ref=TreeNodeRef(milestone_id=milestone_id),
        ),
    )
    tree_store.create_node(
        DEMO_TENANT_ID,
        project_id,
        TreeNodeCreate(
            type=NodeType.note,
            parent_id=root.node_id,
            title="Portfolio Snapshot",
            ref=TreeNodeRef(text="Open the executive portfolio dashboard from Analytics."),
        ),
    )


def _seed_knowledge(knowledge_store: KnowledgeStore, project_id: str, methodology: str) -> None:
    lessons = knowledge_store.list_lessons(project_id=project_id)
    if lessons:
        return
    knowledge_store.create_lesson(
        project_id=project_id,
        stage_id=f"{methodology}-monitoring",
        stage_name="Monitoring & Controlling",
        title=f"{methodology.title()} delivery checkpoint",
        description="Weekly control-tower review captured from seeded demo scenario.",
        tags=["demo", methodology],
        topics=["monitoring", "governance"],
    )


def _seed_demo_entities(demo_outbox: "DemoOutbox | None" = None) -> None:
    fixture = _load_seed_fixture()
    now = datetime.now(tz=timezone.utc).isoformat()
    projects_path = Path(__file__).resolve().parent.parent / "data" / "projects.json"
    existing = {"projects": []}
    if projects_path.exists():
        try:
            existing = json.loads(projects_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {"projects": []}

    items = existing.get("projects", []) if isinstance(existing, dict) else []
    by_id = {item.get("id"): item for item in items if isinstance(item, dict)}

    for project_id, methodology in DEMO_PROJECTS.items():
        by_id[project_id] = {
            "id": project_id,
            "name": f"Demo {methodology.title()} Program",
            "template_id": "predictive-infrastructure" if methodology == "predictive" else "adaptive-software-dev",
            "template_version": "1.0",
            "created_at": now,
            "methodology": {
                "id": methodology,
                "type": methodology,
                "portfolio_id": DEMO_PORTFOLIO_ID,
                "program_id": DEMO_PROGRAM_ID,
            },
            "agent_config": {"enabled": ["agent-01", "agent-10"], "disabled": []},
            "connector_config": {"enabled": ["jira", "sap"], "disabled": []},
            "initial_tabs": [{"type": "document", "title": "Project Charter", "activity_id": None}],
            "dashboards": [{"type": "dashboard", "title": "Portfolio Snapshot", "activity_id": None}],
        }

    projects_path.parent.mkdir(parents=True, exist_ok=True)
    projects_path.write_text(json.dumps({"projects": list(by_id.values())}, indent=2) + "\n", encoding="utf-8")


    if demo_outbox is not None:
        approvals = fixture.get("approvals", [])
        if approvals:
            demo_outbox.write_bucket(
                "approvals",
                [
                    {"tenant_id": DEMO_TENANT_ID, **item}
                    for item in approvals
                    if isinstance(item, dict)
                ],
            )
        connectors = fixture.get("connectors", [])
        if connectors:
            demo_outbox.write_bucket(
                "connectors",
                [
                    {
                        "tenant_id": DEMO_TENANT_ID,
                        "connector_id": f"demo-connector-{index+1}",
                        "name": item.get("title", "Connector"),
                        "status": "configured",
                        "metadata": item.get("data", {}),
                    }
                    for index, item in enumerate(connectors)
                    if isinstance(item, dict)
                ],
            )

    audit_store = get_audit_log_store()
    existing_events = audit_store.list_events(tenant_id=DEMO_TENANT_ID, limit=1)
    if not existing_events:
        audit_store.record_event(
            build_event(
                tenant_id=DEMO_TENANT_ID,
                actor_id="demo-system",
                actor_type="service",
                roles=["seed"],
                action="demo.seed.initialized",
                resource_type="tenant",
                resource_id=DEMO_TENANT_ID,
                outcome="success",
                metadata={
                    "portfolio_id": DEMO_PORTFOLIO_ID,
                    "program_id": DEMO_PROGRAM_ID,
                    "projects": list(DEMO_PROJECTS.keys()),
                    "approvals": fixture.get("approvals", []),
                },
            )
        )




def _seed_enterprise_stores() -> None:
    storage_root = Path(__file__).resolve().parent.parent / "storage"
    demand_path = storage_root / "demand.json"
    if not demand_path.exists() or not json.loads(demand_path.read_text(encoding="utf-8") or "{}").get("items"):
        demand_items = []
        for index in range(30):
            demand_items.append({
                "id": f"dem-{index+1:03d}",
                "portfolio_id": DEMO_PORTFOLIO_ID,
                "title": f"Demand {index+1}",
                "status": ["intake", "analysis", "candidate", "approved"][index % 4],
                "value": 4 + (index % 7),
                "effort": 2 + (index % 5),
                "risk": 1 + (index % 4),
                "cost": 80 + index * 5,
            })
        demand_path.write_text(json.dumps({"items": demand_items}, indent=2) + "\n", encoding="utf-8")

    capacity_path = storage_root / "capacity.json"
    if not capacity_path.exists() or not json.loads(capacity_path.read_text(encoding="utf-8") or "{}").get("entries"):
        roles = ["Engineering", "Product", "QA", "Architecture", "Data"]
        entries = []
        for team in range(1, 6):
            for week in range(1, 7):
                for role in roles:
                    entries.append({
                        "id": f"cap-t{team}-w{week}-{role.lower()}",
                        "portfolio_id": DEMO_PORTFOLIO_ID,
                        "team": f"Team-{team}",
                        "week": f"2026-W{week:02d}",
                        "role": role,
                        "capacity": 40,
                        "allocated": 24 + ((team + week) % 14),
                    })
        capacity_path.write_text(json.dumps({"entries": entries}, indent=2) + "\n", encoding="utf-8")

    scenarios_path = storage_root / "scenarios.json"
    if not scenarios_path.exists() or not json.loads(scenarios_path.read_text(encoding="utf-8") or "{}").get("scenarios"):
        scenarios = [
            {"id": "scn-balanced", "portfolio_id": DEMO_PORTFOLIO_ID, "name": "Balanced", "value_score": 78.2, "budget": 1820, "selected_ids": [f"dem-{i:03d}" for i in range(1, 11)], "published": False},
            {"id": "scn-growth", "portfolio_id": DEMO_PORTFOLIO_ID, "name": "Growth", "value_score": 85.6, "budget": 2180, "selected_ids": [f"dem-{i:03d}" for i in range(8, 18)], "published": False},
            {"id": "scn-efficiency", "portfolio_id": DEMO_PORTFOLIO_ID, "name": "Efficiency", "value_score": 74.9, "budget": 1500, "selected_ids": [f"dem-{i:03d}" for i in range(18, 28)], "published": False},
        ]
        scenarios_path.write_text(json.dumps({"scenarios": scenarios, "published_decisions": []}, indent=2) + "\n", encoding="utf-8")


def seed_demo_data(
    *,
    workspace_state_store: WorkspaceStateStore,
    spreadsheet_store: SpreadsheetStore,
    timeline_store: TimelineStore,
    tree_store: TreeStore,
    knowledge_db_path: Path,
    demo_outbox: "DemoOutbox | None" = None,
) -> None:
    _seed_demo_entities(demo_outbox=demo_outbox)
    _seed_enterprise_stores()
    knowledge_store = KnowledgeStore(knowledge_db_path)
    for project_id, methodology in DEMO_PROJECTS.items():
        _seed_workspace_state(workspace_state_store, project_id, methodology)
        sheet_id = _seed_sheet(spreadsheet_store, project_id)
        milestone_id = _seed_timeline(timeline_store, project_id)
        _seed_tree_artifacts(tree_store, project_id, sheet_id, milestone_id)
        _seed_knowledge(knowledge_store, project_id, methodology)

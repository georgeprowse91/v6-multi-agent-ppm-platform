from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st

try:
    import yaml
except ImportError:  # pragma: no cover - fallback for minimal runtime images
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_ROOT = Path(__file__).resolve().parent
CONVERSATIONS_DIR = REPO_ROOT / "apps/web/data/demo_conversations"
OUTBOX_PATH = DEMO_ROOT / "storage/demo_outbox.json"


@dataclass(frozen=True)
class Scenario:
    id: str
    label: str


@dataclass(frozen=True)
class DemoActivity:
    id: str
    name: str


@dataclass(frozen=True)
class DemoStage:
    id: str
    name: str
    activities: list[DemoActivity]


@dataclass(frozen=True)
class DemoMethodology:
    id: str
    name: str
    stages: list[DemoStage]


@dataclass(frozen=True)
class AgentCapability:
    agent_id: str
    name: str
    domain: str
    capability: str


@dataclass(frozen=True)
class Chip:
    label: str
    action: str
    payload: dict[str, Any] | None = None


DATASET_FILES: dict[str, Path] = {
    "projects": REPO_ROOT / "apps/web/data/projects.json",
    "demo_seed": REPO_ROOT / "apps/web/data/demo_seed.json",
    "demo_run_log": REPO_ROOT / "apps/web/data/demo/demo_run_log.json",
    "portfolio_health": REPO_ROOT / "examples/demo-scenarios/portfolio-health.json",
    "lifecycle_metrics": REPO_ROOT / "examples/demo-scenarios/lifecycle-metrics.json",
    "workflow_monitoring": REPO_ROOT / "examples/demo-scenarios/workflow-monitoring.json",
    "approvals": REPO_ROOT / "examples/demo-scenarios/approvals.json",
    "assistant_responses": REPO_ROOT / "examples/demo-scenarios/assistant-responses.json",
    "feature_flags": DEMO_ROOT / "data/feature_flags_demo.json",
    "storage_notifications": REPO_ROOT / "apps/web/storage/notifications.json",
    "storage_scenarios": REPO_ROOT / "apps/web/storage/scenarios.json",
    "dashboard_approvals": REPO_ROOT / "apps/web/data/demo_dashboards/approvals.json",
    "dashboard_portfolio_health": REPO_ROOT / "apps/web/data/demo_dashboards/portfolio-health.json",
    "dashboard_lifecycle": REPO_ROOT / "apps/web/data/demo_dashboards/lifecycle-metrics.json",
    "dashboard_workflow": REPO_ROOT / "apps/web/data/demo_dashboards/workflow-monitoring.json",
    "dashboard_executive": REPO_ROOT / "apps/web/data/demo_dashboards/executive_portfolio.json",
}

AGENT_CATALOG_PATH = REPO_ROOT / "agents/AGENT_CATALOG.md"
CONNECTOR_MANIFEST_GLOB = REPO_ROOT / "integrations/connectors/*/manifest.yaml"
TEMPLATES_PATH = REPO_ROOT / "apps/web/data/templates.json"


def slugify(value: str) -> str:
    return (
        "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split()) or "unknown"
    )


def friendly_label(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def load_methodologies() -> list[dict[str, Any]]:
    payload = json.loads(DATASET_FILES["storage_scenarios"].read_text(encoding="utf-8"))
    methodologies = payload.get("methodologies")
    if not isinstance(methodologies, list) or not methodologies:
        raise ValueError("scenarios.json must include a non-empty top-level methodologies array.")
    return methodologies


def parse_methodologies(raw_methodologies: list[dict[str, Any]]) -> list[DemoMethodology]:
    methodologies: list[DemoMethodology] = []
    for method in raw_methodologies:
        stages: list[DemoStage] = []
        for stage in method.get("stages", []):
            stage_activities = [
                DemoActivity(id=str(activity["activity_id"]), name=str(activity["activity_name"]))
                for activity in stage.get("activities", [])
            ]
            stages.append(
                DemoStage(id=str(stage["id"]), name=str(stage["name"]), activities=stage_activities)
            )
        methodologies.append(
            DemoMethodology(id=str(method["id"]), name=str(method["name"]), stages=stages)
        )
    return methodologies


def load_conversation_scenarios() -> list[Scenario]:
    return [
        Scenario(id=path.stem, label=friendly_label(path.stem))
        for path in sorted(CONVERSATIONS_DIR.glob("*.json"))
    ]


def parse_agent_capabilities() -> list[AgentCapability]:
    if not AGENT_CATALOG_PATH.exists():
        return []
    content = AGENT_CATALOG_PATH.read_text(encoding="utf-8")
    capabilities: list[AgentCapability] = []
    current_domain = "General"
    for line in content.splitlines():
        if line.startswith("## "):
            current_domain = line.replace("##", "").strip()
            continue
        match = re.match(r"### Agent (\d+): (.+?) \(`(agent-[^`]+)`\)", line)
        if not match:
            continue
        agent_num, capability_name, slug = match.groups()
        capabilities.append(
            AgentCapability(
                agent_id=f"agent-{int(agent_num):02d}",
                name=slug.replace("-", " ").title(),
                domain=current_domain,
                capability=capability_name.strip(),
            )
        )
    return capabilities


def load_connector_registry() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for manifest in sorted(REPO_ROOT.glob("integrations/connectors/*/manifest.yaml")):
        connector_id = manifest.parent.name
        raw = manifest.read_text(encoding="utf-8")
        payload: dict[str, Any] = {}
        if yaml is not None:
            parsed = yaml.safe_load(raw)
            if isinstance(parsed, dict):
                payload = parsed
        if not payload:
            name_match = re.search(r"^name:\s*(.+)$", raw, flags=re.MULTILINE)
            payload["name"] = name_match.group(1).strip() if name_match else connector_id
        rows.append(
            {
                "connector_id": connector_id,
                "name": payload.get("name", connector_id.replace("_", " ").title()),
                "version": payload.get("version", "n/a"),
                "category": payload.get("category", payload.get("type", "connector")),
                "status": payload.get("status", "active"),
                "path": str(manifest.relative_to(REPO_ROOT)),
            }
        )
    return rows


def load_methodology_activity_details() -> dict[str, dict[str, str]]:
    if not TEMPLATES_PATH.exists():
        return {}
    payload = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    details: dict[str, dict[str, str]] = {}
    for template in payload.get("templates", []):
        methodology = template.get("methodology", {})
        for stage in methodology.get("stages", []):
            for activity in stage.get("activities", []):
                activity_id = str(activity.get("id") or activity.get("activity_id") or "")
                if not activity_id:
                    continue
                details[activity_id] = {
                    "description": str(
                        activity.get("description")
                        or f"Deliver {activity.get('name', activity_id)} outcomes."
                    ),
                    "canvas_type": str(activity.get("canvasType") or "document"),
                    "status": str(activity.get("status") or "not_started"),
                }
    return details


class DemoOutbox:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def append(self, bucket: str, payload: dict[str, Any]) -> None:
        state = self._load()
        state.setdefault(bucket, []).append(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    def read(self) -> dict[str, Any]:
        return self._load()


class DemoDataHub:
    def __init__(self) -> None:
        self._payloads: dict[str, Any] = {}
        self.provenance: dict[str, list[str]] = {}

    def load(self, key: str) -> Any:
        if key not in self._payloads:
            if key in DATASET_FILES:
                self._payloads[key] = json.loads(DATASET_FILES[key].read_text(encoding="utf-8"))
            else:
                self._payloads[key] = json.loads(
                    (CONVERSATIONS_DIR / f"{key}.json").read_text(encoding="utf-8")
                )
        return self._payloads[key]

    def _record(self, view: str, dataset_keys: list[str]) -> None:
        self.provenance[view] = dataset_keys

    def normalized_projects(self) -> list[dict[str, Any]]:
        self._record("Workspace", ["projects", "demo_seed", "storage_scenarios"])
        projects = self.load("projects").get("projects", [])
        seed = self.load("demo_seed")
        rows: list[dict[str, Any]] = []
        for project in projects:
            rows.append(
                {
                    "id": project.get("id", project.get("project_id", "unknown")),
                    "name": project.get("name", project.get("title", "Untitled")),
                    "status": project.get("status", "In Progress"),
                    "owner": project.get("owner", "Demo Owner"),
                }
            )
        for item in seed.get("portfolios", []):
            rows.append(
                {
                    "id": item.get("data", {}).get("portfolio_id", "demo-portfolio"),
                    "name": item.get("title", "Demo Portfolio"),
                    "status": item.get("status", "Active"),
                    "owner": "PMO",
                }
            )
        dedup = {row["id"]: row for row in rows}
        return sorted(dedup.values(), key=lambda row: str(row["name"]).lower())

    def normalized_entities(self) -> dict[str, list[dict[str, Any]]]:
        self._record("Collections", ["projects", "demo_seed"])
        seed = self.load("demo_seed")

        portfolios: list[dict[str, Any]] = []
        for item in seed.get("portfolios", []):
            data = item.get("data", {}) if isinstance(item, dict) else {}
            portfolios.append(
                {
                    "id": data.get("portfolio_id", slugify(item.get("title", "portfolio"))),
                    "name": item.get("title", "Portfolio"),
                    "status": item.get("status", "Active"),
                    "owner": data.get("owner", "PMO"),
                    "classification": item.get("classification", "Internal"),
                }
            )

        projects: list[dict[str, Any]] = []
        raw_projects = self.load("projects").get("projects", [])
        for i, item in enumerate(raw_projects, start=1):
            projects.append(
                {
                    "id": item.get("id") or item.get("project_id") or f"demo-project-{i}",
                    "name": item.get("name") or item.get("title") or f"Demo Project {i}",
                    "status": item.get("status", "In Progress"),
                    "owner": item.get("owner", "Project Lead"),
                    "program_id": item.get("program_id", "demo-program-01"),
                    "portfolio_id": item.get("portfolio_id", "demo-portfolio"),
                }
            )

        if not projects:
            for i in range(1, 4):
                projects.append(
                    {
                        "id": f"demo-project-{i:02d}",
                        "name": ["Phoenix Modernization", "Atlas Migration", "Nova Compliance"][
                            i - 1
                        ],
                        "status": ["In Progress", "At Risk", "Planning"][i - 1],
                        "owner": ["R. Chen", "A. Thomas", "P. Iyer"][i - 1],
                        "program_id": "demo-program-01",
                        "portfolio_id": "demo-portfolio",
                    }
                )

        programs = [
            {
                "id": "demo-program-01",
                "name": "Digital Transformation",
                "status": "In Progress",
                "owner": "PMO Strategy",
                "portfolio_id": "demo-portfolio",
            },
            {
                "id": "demo-program-02",
                "name": "Risk & Controls",
                "status": "Planning",
                "owner": "Governance Office",
                "portfolio_id": "demo-portfolio",
            },
        ]

        return {"portfolios": portfolios, "programs": programs, "projects": projects}

    def normalized_intake_requests(self) -> list[dict[str, Any]]:
        self._record("Intake", ["dashboard_approvals", "projects"])
        projects = self.normalized_entities()["projects"]
        rows: list[dict[str, Any]] = []
        for idx, project in enumerate(projects[:3], start=1):
            rows.append(
                {
                    "request_id": f"intake-{idx:03d}",
                    "title": f"{project['name']} intake",
                    "requester": ["Sophie Lang", "Marcus Reed", "Priya Shah"][idx - 1],
                    "status": "approved" if idx < 3 else "pending",
                    "submitted_at": f"2026-02-{10+idx}T09:00:00Z",
                    "decision_at": f"2026-02-{11+idx}T14:00:00Z" if idx < 3 else None,
                    "project_id": project["id"],
                    "approval_type": ["stage_gate", "template", "publish"][idx - 1],
                }
            )
        return rows

    def normalized_agent_catalog(self) -> list[dict[str, Any]]:
        self._record("Agents", ["demo_run_log"])
        run_agents = {
            str(run.get("agent_id")): run for run in self.load("demo_run_log").get("agents", [])
        }
        capabilities = parse_agent_capabilities()
        rows: list[dict[str, Any]] = []
        for idx, capability in enumerate(capabilities, start=1):
            run = run_agents.get(capability.agent_id, {})
            rows.append(
                {
                    "agent_id": capability.agent_id,
                    "name": capability.name,
                    "domain": capability.domain,
                    "capability": capability.capability,
                    "last_status": run.get("status", "ready"),
                    "avg_duration_seconds": run.get("duration_seconds", 45),
                    "version": f"v1.{idx}",
                }
            )

        if rows:
            return rows

        for idx, (agent_id, run) in enumerate(sorted(run_agents.items()), start=1):
            rows.append(
                {
                    "agent_id": agent_id,
                    "name": f"{agent_id.upper()} · Delivery Agent",
                    "domain": "General",
                    "capability": ["Intake", "Planning", "Risk", "Quality"][idx % 4],
                    "last_status": run.get("status", "completed"),
                    "avg_duration_seconds": run.get("duration_seconds", 45),
                    "version": f"v1.{idx}",
                }
            )
        return rows

    def normalized_artifact_lifecycle(self) -> list[dict[str, Any]]:
        self._record("Artifact Lifecycle", ["demo_run_log", "dashboard_approvals"])
        run_agents = self.load("demo_run_log").get("agents", [])
        approvals = self.load("dashboard_approvals").get("approvals", [])
        rows: list[dict[str, Any]] = []
        statuses = ["generated", "in_review", "approved", "published"]
        for idx, run in enumerate(run_agents[:8], start=1):
            lifecycle = statuses[idx % len(statuses)]
            rows.append(
                {
                    "artifact_id": f"artifact-{idx:03d}",
                    "artifact_type": ["status_report", "timeline", "decision_log", "risk_register"][
                        idx % 4
                    ],
                    "project_id": "demo-project-01",
                    "status": lifecycle,
                    "required_approvals": 2,
                    "approved_count": 2 if lifecycle in {"approved", "published"} else 1,
                    "publish_ready": lifecycle in {"approved", "published"},
                    "audit_event_id": f"audit-lifecycle-{idx:03d}",
                    "linked_approval": (
                        approvals[idx % len(approvals)].get("title", "Gate approval")
                        if approvals
                        else "Gate approval"
                    ),
                    "agent_id": run.get("agent_id", "agent-01"),
                }
            )
        return rows

    def normalized_dashboard(self) -> dict[str, Any]:
        self._record(
            "Dashboard",
            ["portfolio_health", "lifecycle_metrics", "workflow_monitoring", "approvals"],
        )
        return {
            "health": self.load("portfolio_health"),
            "lifecycle": self.load("lifecycle_metrics"),
            "workflow": self.load("workflow_monitoring"),
            "approvals": self.load("approvals"),
        }

    def normalized_approvals(self) -> list[dict[str, Any]]:
        self._record("Approvals", ["approvals", "demo_seed"])
        seed_approvals = self.load("demo_seed").get("approvals", [])
        base = self.load("approvals").get("approvals", [])
        rows: list[dict[str, Any]] = []
        for item in base:
            rows.append(
                {"title": item.get("title", "Untitled"), "approvers": item.get("approvers", "N/A")}
            )
        for item in seed_approvals:
            rows.append(
                {
                    "title": item.get("title", "Untitled"),
                    "approvers": ", ".join(item.get("required_approvers", [])),
                    "status": item.get("status", "pending"),
                }
            )
        return rows

    def normalized_notifications(self) -> list[dict[str, Any]]:
        self._record("Notifications", ["demo_seed", "storage_notifications"])
        rows = self.load("demo_seed").get("notifications", [])
        storage_rows = self.load("storage_notifications").get("notifications", [])
        return rows + storage_rows

    def normalized_audit(self) -> list[dict[str, Any]]:
        self._record("Audit", ["demo_seed"])
        return self.load("demo_seed").get("audit_log", [])

    def normalized_connectors(self) -> list[dict[str, Any]]:
        self._record("Connectors", ["demo_seed"])
        registry = load_connector_registry()
        if registry:
            return registry
        return self.load("demo_seed").get("connectors", [])

    def methodology_activity_details(self) -> dict[str, dict[str, str]]:
        self._record("Workspace", ["storage_scenarios"])
        return load_methodology_activity_details()

    def normalized_demo_run(self) -> dict[str, Any]:
        self._record("Demo Run", ["demo_run_log", "workflow_monitoring"])
        return self.load("demo_run_log")

    def feature_flags(self) -> dict[str, bool]:
        return self.load("feature_flags")

    def methodologies(self) -> list[DemoMethodology]:
        self._record("Workspace", ["storage_scenarios"])
        return parse_methodologies(load_methodologies())

    def assistant_script(self, scenario_id: str) -> list[dict[str, str]]:
        self._record("Assistant", [scenario_id])
        script_blob = self.load(scenario_id)
        if isinstance(script_blob, list):
            return script_blob
        if isinstance(script_blob, dict) and isinstance(script_blob.get("messages"), list):
            return script_blob["messages"]
        return []

    def assistant_responses(self) -> dict[str, Any]:
        return self.load("assistant_responses")


class DemoRunEngine:
    def __init__(self, run_log: dict[str, Any], outbox: DemoOutbox) -> None:
        self.run_log = run_log
        self.outbox = outbox

    def progress(self, step: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        agents = self.run_log.get("agents", [])
        return agents[:step], agents[step:]

    def play_step(self, step: int) -> int:
        agents = self.run_log.get("agents", [])
        if step >= len(agents):
            return step
        agent = agents[step]
        event = {
            "event_id": f"demo-run-{uuid4().hex[:10]}",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "agent_id": agent.get("agent_id"),
            "status": agent.get("status"),
            "duration_seconds": agent.get("duration_seconds"),
            "artifacts": agent.get("artifacts", []),
        }
        self.outbox.append("demo_run_events", event)
        self.outbox.append(
            "audit_events",
            {
                "event_id": f"demo-audit-{uuid4().hex[:10]}",
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "action": "demo.agent.executed",
                "resource_type": "agent",
                "resource_id": agent.get("agent_id"),
            },
        )
        return step + 1


@st.cache_resource(show_spinner=False)
def get_data_hub() -> DemoDataHub:
    return DemoDataHub()


def find_methodology(
    methodologies: list[DemoMethodology], method_id: str
) -> DemoMethodology | None:
    return next((m for m in methodologies if m.id == method_id), None)


def find_stage(method: DemoMethodology | None, stage_id: str) -> DemoStage | None:
    if method is None:
        return None
    return next((s for s in method.stages if s.id == stage_id), None)


def inject_demo_styles() -> None:
    st.markdown(
        """
        <style>
          .stApp [data-testid="stMetric"] {
            background: linear-gradient(180deg, #ffffff, #f8fafc);
            border: 1px solid #dbe5f1;
            border-radius: 14px;
            padding: 0.65rem 0.8rem;
          }
          .stApp [data-testid="stMetricLabel"] {
            font-weight: 600;
          }
          .stApp [data-testid="stSidebar"] {
            border-right: 1px solid #e2e8f0;
          }
          .stApp h1, .stApp h2, .stApp h3 {
            letter-spacing: -0.01em;
          }
          .stApp [data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_global_context_bar() -> None:
    st.caption(
        " | ".join(
            [
                f"**Project:** {st.session_state.get('selected_project') or 'Not selected'}",
                f"**Methodology:** {st.session_state.get('selected_methodology_name') or 'N/A'}",
                f"**Stage:** {st.session_state.get('selected_stage_name') or 'N/A'}",
                f"**Activity:** {st.session_state.get('selected_activity_name') or 'N/A'}",
                f"**Outcome:** {st.session_state.get('selected_outcome') or 'on_track'}",
            ]
        )
    )


def sync_methodology_state(hub: DemoDataHub) -> None:
    try:
        methodologies = hub.methodologies()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    if not methodologies:
        st.error("scenarios.json is missing a non-empty methodologies array.")
        st.stop()

    method_ids = [m.id for m in methodologies]
    if st.session_state.get("selected_methodology_id") not in method_ids:
        st.session_state["selected_methodology_id"] = method_ids[0]

    method = find_methodology(methodologies, st.session_state["selected_methodology_id"])
    if method is None or not method.stages:
        st.error("Selected methodology must include at least one stage.")
        st.stop()

    stage_ids = [s.id for s in method.stages]
    if st.session_state.get("selected_stage_id") not in stage_ids:
        st.session_state["selected_stage_id"] = stage_ids[0]

    stage = find_stage(method, st.session_state.get("selected_stage_id", ""))
    if stage is None or not stage.activities:
        st.error("Selected stage has no activities in scenarios.json.")
        st.stop()

    activity_ids = [a.id for a in stage.activities]
    if st.session_state.get("selected_activity_id") not in activity_ids:
        st.session_state["selected_activity_id"] = activity_ids[0]

    activity = next(
        (a for a in stage.activities if a.id == st.session_state["selected_activity_id"]), None
    )
    if activity is None:
        st.error("Selected activity is invalid for the selected stage.")
        st.stop()

    st.session_state["selected_methodology_name"] = method.name
    st.session_state["selected_stage_name"] = stage.name
    st.session_state["selected_activity_name"] = activity.name


def render_scenario_selectors_sidebar(hub: DemoDataHub) -> None:
    try:
        methodologies = hub.methodologies()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    method_ids = [m.id for m in methodologies]
    st.session_state["selected_methodology_id"] = st.sidebar.selectbox(
        "Methodology",
        method_ids,
        index=method_ids.index(st.session_state["selected_methodology_id"]),
        format_func=lambda method_id: next(
            (m.name for m in methodologies if m.id == method_id), method_id
        ),
    )
    sync_methodology_state(hub)

    selected_method = find_methodology(methodologies, st.session_state["selected_methodology_id"])
    stage_ids = [s.id for s in selected_method.stages]
    st.session_state["selected_stage_id"] = st.sidebar.selectbox(
        "Stage",
        stage_ids,
        index=stage_ids.index(st.session_state["selected_stage_id"]),
        format_func=lambda stage_id: next(
            (s.name for s in selected_method.stages if s.id == stage_id), stage_id
        ),
    )
    sync_methodology_state(hub)

    selected_stage = find_stage(selected_method, st.session_state["selected_stage_id"])
    activity_ids = [a.id for a in selected_stage.activities]
    st.session_state["selected_activity_id"] = st.sidebar.selectbox(
        "Activity",
        activity_ids,
        index=activity_ids.index(st.session_state["selected_activity_id"]),
        format_func=lambda activity_id: next(
            (a.name for a in selected_stage.activities if a.id == activity_id), activity_id
        ),
    )
    sync_methodology_state(hub)


def scenario_restart(script: list[dict[str, str]]) -> None:
    st.session_state["assistant_messages"] = []
    st.session_state["assistant_step"] = 0
    if script and script[0].get("role") == "assistant":
        st.session_state["assistant_messages"].append(script[0])
        st.session_state["assistant_step"] = 1


def init_state(hub: DemoDataHub) -> None:
    scenarios = load_conversation_scenarios()
    default_scenario = scenarios[0].id if scenarios else ""
    defaults: dict[str, Any] = {
        "selected_page": "Home",
        "active_page": "Home",
        "selected_project": None,
        "selected_methodology_id": None,
        "selected_methodology_name": "",
        "selected_stage_id": None,
        "selected_stage_name": "",
        "selected_activity_id": None,
        "selected_activity_name": "",
        "selected_status": "on_track",
        "selected_outcome": "on_track",
        "selected_scenario": default_scenario,
        "assistant_messages": [],
        "assistant_step": 0,
        "assistant_prompt": "",
        "assistant_last_artifact": None,
        "completed_activity_ids": set(),
        "demo_run_step": 0,
        "feature_flags": hub.feature_flags(),
        "collection_type": "projects",
        "collection_search": "",
        "selected_intake_request": None,
        "selected_agent_id": None,
        "selected_invocation_agent": "agent-01",
        "selected_approval_type": "all",
        "what_if_budget_delta": 0,
        "what_if_scope_delta": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    sync_methodology_state(hub)


def append_outbox_event(outbox: DemoOutbox, event_type: str, payload: dict[str, Any]) -> None:
    outbox.append(
        "assistant_actions",
        {
            "type": event_type,
            "ts": datetime.now(tz=UTC).isoformat(),
            **payload,
        },
    )


_RAG_LABEL = {"on_track": "🟢 On Track", "at_risk": "🟡 At Risk", "off_track": "🔴 Off Track"}


def generate_artifact_content(artifact_type: str, artifact_format: str) -> tuple[str, str]:
    project_id = st.session_state.get("selected_project") or "demo-project-01"
    method_name = st.session_state.get("selected_methodology_name") or "Predictive"
    stage_name = st.session_state.get("selected_stage_name") or "Discover"
    activity_name = st.session_state.get("selected_activity_name") or "Activity"
    outcome = st.session_state.get("selected_outcome") or "on_track"
    rag = _RAG_LABEL.get(outcome, "🟢 On Track")
    timestamp = datetime.now(tz=UTC).isoformat()

    if artifact_format == "csv":
        content = (
            "artifact_type,project_id,methodology,stage,activity,outcome,rag_status,generated_at\n"
            f"{artifact_type},{project_id},{method_name},{stage_name},{activity_name},{outcome},{rag},{timestamp}\n"
        )
        return content, "text/csv"

    if artifact_format == "txt":
        content = (
            f"Artifact Type : {artifact_type}\n"
            f"Project       : {project_id}\n"
            f"Methodology   : {method_name}\n"
            f"Stage         : {stage_name}\n"
            f"Activity      : {activity_name}\n"
            f"RAG Status    : {rag}\n"
            f"Generated     : {timestamp}\n"
        )
        return content, "text/plain"

    # Rich markdown — template varies by artifact_type
    if artifact_type == "status_report":
        content = f"""# Weekly Status Report — {project_id}

**Period:** {timestamp[:10]}  **Methodology:** {method_name}  **Stage:** {stage_name}
**Activity:** {activity_name}  **Overall Status:** {rag}

---

## Executive Summary

Project is progressing through the **{stage_name}** stage with status **{rag}**.
Current activity in focus: *{activity_name}*.

## Milestone Tracker

| Milestone | Planned | Status |
|-----------|---------|--------|
| {activity_name} | This week | {rag} |
| Stage gate review | Next week | Scheduled |

## Budget

- Actuals to date: £742k of £1.2M (62%)
- Forecast at completion: £1.19M (within tolerance)
- CPI: 1.02 ✅ | SPI: 0.97 🟡

## Risk Summary

- Open risks: 9 (1 High, 3 Medium, 5 Low)
- Risk exposure: 32% (threshold: 25%) {"⚠️ Above threshold" if outcome != "on_track" else "✅"}

## Next Period Focus

- Complete {activity_name}
- Prepare gate pack for review
- Resolve outstanding RAID items

---
*Generated: {timestamp}*
"""
    elif artifact_type == "risk_register":
        content = f"""# Risk Register — {project_id}

**Stage:** {stage_name}  **As of:** {timestamp[:10]}  **Overall Status:** {rag}

---

| # | Risk | Likelihood | Impact | Score | Owner | Mitigation | Status |
|---|------|-----------|--------|-------|-------|------------|--------|
| R01 | Identity provider integration delay | High | High | 🔴 16 | L. Chen | Fallback auth owner assigned | Escalated |
| R02 | Contractor rate increase | Medium | Medium | 🟡 9 | S. Lang | Budget change request raised | Active |
| R03 | Data classification approval | Medium | Low | 🟡 6 | H. Cole | Compliance review in progress | Active |
| R04 | API schema freeze delay | Low | Medium | 🟢 4 | T. Nguyen | Schema freeze confirmed this week | Monitoring |
| R05 | UAT resource availability | Low | Low | 🟢 2 | A. Lee | Capacity confirmed | Closed |

## RAID Summary

- **Risks:** 9 open (1H, 3M, 5L)
- **Assumptions:** 3 unvalidated
- **Issues:** 1 active (identity provider)
- **Dependencies:** 3 in RAID log

---
*Generated: {timestamp}*
"""
    elif artifact_type == "decision_log":
        content = f"""# Decision Log — {project_id}

**Stage:** {stage_name}  **Activity:** {activity_name}  **As of:** {timestamp[:10]}

---

| # | Decision | Date | Owner | Rationale | Impact |
|---|----------|------|-------|-----------|--------|
| D01 | Proceed with contractor option for sprint 5–7 resourcing | {timestamp[:10]} | M. Chen | Fastest mobilisation, within contingency | +£52k, -2 week lag |
| D02 | Select Northstar Security as preferred vendor | {timestamp[:10]} | H. Cole | Highest compliance posture (SOC2, data residency) | Procurement approved |
| D03 | Extend sprint 6 by 2 weeks pending vendor integration | {timestamp[:10]} | E. Brooks | Risk mitigation — identity provider dependency | +2 weeks, £18k draw |
| D04 | Architecture sign-off accepted with conditions | {timestamp[:10]} | K. Patel | Encryption at rest confirmation pending from vendor | Gate conditional |

## Open Decisions

- Budget supplement £25k — awaiting Sophie Lang and Elena Brooks approval (SLA: 8h)

---
*Generated: {timestamp}*
"""
    elif artifact_type == "timeline":
        content = f"""# Project Timeline — {project_id}

**Methodology:** {method_name}  **Stage:** {stage_name}  **Status:** {rag}

---

## Milestone Schedule

| Milestone | Baseline | Forecast | Status |
|-----------|----------|----------|--------|
| Charter sign-off | 2026-02-28 | 2026-02-28 | ✅ On track |
| Design Gate exit | 2026-03-14 | 2026-03-14 | 🟡 Conditional |
| Sprint 5 start | 2026-03-17 | 2026-03-17 | ✅ On track |
| Sprint 6 start | 2026-03-31 | 2026-04-14 | {"🔴 At risk +2w" if outcome != "on_track" else "✅ On track"} |
| UAT Phase 2 | 2026-04-07 | 2026-04-21 | {"🔴 Delayed" if outcome == "off_track" else "🟡 Monitoring"} |
| Go-live | 2026-04-28 | 2026-05-12 | {"🔴 At risk" if outcome != "on_track" else "✅ On track"} |

## Summary

- **Schedule variance:** {"−14 days (rebaseline pending)" if outcome != "on_track" else "0 days"}
- **Critical path:** Identity provider integration → Sprint 6 → UAT Phase 2 → Go-live
- **SPI:** {"0.87" if outcome == "off_track" else "0.97"}

---
*Generated: {timestamp}*
"""
    else:
        title = artifact_type.replace("_", " ").title()
        content = f"""# {title} — {project_id}

**Methodology:** {method_name}  **Stage:** {stage_name}  **Activity:** {activity_name}
**Status:** {rag}  **Generated:** {timestamp[:10]}

---

## Summary

Artifact generated for the **{activity_name}** activity in the {stage_name} stage of the
{method_name} methodology. Current delivery status is {rag}.

## Key Outputs

- Scope and objectives documented for {activity_name}
- Evidence package assembled and linked to audit trail
- Stakeholders notified and approval routing initiated
- Next activity recommended: stage gate review

## Metadata

| Attribute | Value |
|-----------|-------|
| Project | {project_id} |
| Methodology | {method_name} |
| Stage | {stage_name} |
| Activity | {activity_name} |
| RAG Status | {rag} |
| Generated | {timestamp} |

---
*This artifact was generated by the demo assistant. All data is illustrative.*
"""

    return content, "text/markdown"


def handle_chip(chip: Chip, outbox: DemoOutbox) -> None:
    payload = chip.payload or {}
    if chip.action == "NAVIGATE":
        page = payload.get("page")
        if isinstance(page, str):
            st.session_state["active_page"] = page
            st.session_state["selected_page"] = page
    elif chip.action == "OPEN_ACTIVITY":
        stage_id = payload.get("stage_id")
        activity_id = payload.get("activity_id")
        if isinstance(stage_id, str) and isinstance(activity_id, str):
            st.session_state["selected_stage_id"] = stage_id
            st.session_state["selected_activity_id"] = activity_id
    elif chip.action == "COMPLETE_ACTIVITY":
        stage_id = str(payload.get("stage_id") or st.session_state.get("selected_stage_id") or "")
        activity_id = str(
            payload.get("activity_id") or st.session_state.get("selected_activity_id") or ""
        )
        if activity_id:
            st.session_state["completed_activity_ids"].add(activity_id)
            append_outbox_event(
                outbox, "activity.completed", {"stage_id": stage_id, "activity_id": activity_id}
            )
    elif chip.action == "GENERATE_ARTIFACT":
        artifact_type = str(payload.get("artifact_type") or "status_report")
        artifact_format = str(payload.get("artifact_format") or "md")
        content, mime_type = generate_artifact_content(artifact_type, artifact_format)
        file_name = f"{artifact_type}_{slugify(st.session_state.get('selected_activity_name') or 'artifact')}.{artifact_format}"
        st.session_state["assistant_last_artifact"] = {
            "artifact_type": artifact_type,
            "content": content,
            "file_name": file_name,
            "mime_type": mime_type,
        }
        append_outbox_event(
            outbox,
            "artifact.generated",
            {
                "artifact_type": artifact_type,
                "artifact_format": artifact_format,
                "file_name": file_name,
                "stage_id": st.session_state.get("selected_stage_id"),
                "activity_id": st.session_state.get("selected_activity_id"),
                "project_id": st.session_state.get("selected_project"),
            },
        )


def get_action_chips() -> list[Chip]:
    stage = (st.session_state.get("selected_stage_name") or "").lower()
    outcome = st.session_state.get("selected_outcome") or "on_track"
    stage_id = st.session_state.get("selected_stage_id")
    activity_id = st.session_state.get("selected_activity_id")

    # Stage-specific primary artifact chip
    _stage_artifacts: dict[str, tuple[str, str]] = {
        "discover": ("Draft charter brief", "status_report"),
        "design": ("Generate WBS baseline", "timeline"),
        "deliver": ("Generate status report", "status_report"),
        "embed": ("Generate lessons learned", "decision_log"),
    }
    artifact_label, artifact_type = _stage_artifacts.get(stage, ("Generate artifact", "status_report"))

    chips: list[Chip] = [
        Chip(label="Go to Dashboard", action="NAVIGATE", payload={"page": "Dashboard"}),
        Chip(
            label="Open selected activity",
            action="OPEN_ACTIVITY",
            payload={"stage_id": stage_id, "activity_id": activity_id},
        ),
        Chip(
            label="Complete current activity",
            action="COMPLETE_ACTIVITY",
            payload={"stage_id": stage_id, "activity_id": activity_id},
        ),
        Chip(
            label=artifact_label,
            action="GENERATE_ARTIFACT",
            payload={"artifact_type": artifact_type, "artifact_format": "md"},
        ),
    ]

    # Add escalation chip when at risk or off track
    if outcome == "at_risk":
        chips.append(
            Chip(
                label="Generate risk register",
                action="GENERATE_ARTIFACT",
                payload={"artifact_type": "risk_register", "artifact_format": "md"},
            )
        )
    elif outcome == "off_track":
        chips.append(
            Chip(
                label="Generate decision log",
                action="GENERATE_ARTIFACT",
                payload={"artifact_type": "decision_log", "artifact_format": "md"},
            )
        )

    return chips


def _load_outcome_variants() -> dict[str, Any]:
    path = DEMO_ROOT / "data/assistant_outcome_variants.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _detect_action(prompt: str) -> str:
    lowered = prompt.lower()
    if any(w in lowered for w in ("generate", "create", "draft", "write", "produce", "build")):
        return "generate"
    if any(w in lowered for w in ("review", "check", "assess", "evaluate", "analyse", "analyze")):
        return "review"
    if any(w in lowered for w in ("publish", "submit", "send", "share", "approve", "release")):
        return "publish"
    return "generate"


def choose_assistant_response(hub: DemoDataHub, prompt: str) -> tuple[str, str]:
    variants = _load_outcome_variants()
    scenario_id = st.session_state.get("selected_scenario", "")
    activity_name = st.session_state.get("selected_activity_name", "")
    stage_name = st.session_state.get("selected_stage_name", "")
    outcome = st.session_state.get("selected_outcome", "on_track")
    action = _detect_action(prompt)

    # 1. Try by_scenario → "default" bucket → outcome → action
    by_scenario = variants.get("by_scenario", {})
    if scenario_id in by_scenario:
        bucket = by_scenario[scenario_id].get("default", {})
        text = bucket.get(outcome, {}).get(action) or bucket.get("on_track", {}).get(action)
        if text:
            return str(text), f"variants.by_scenario.{scenario_id}"

    # 2. Try by_activity (lowercase match)
    by_activity = variants.get("by_activity", {})
    bucket = by_activity.get(activity_name.lower(), {})
    text = bucket.get(outcome, {}).get(action) or bucket.get("on_track", {}).get(action)
    if text:
        return str(text), "variants.by_activity"

    # 3. Try by_stage (lowercase match)
    by_stage = variants.get("by_stage", {})
    bucket = by_stage.get(stage_name.lower(), {})
    text = bucket.get(outcome, {}).get(action) or bucket.get("on_track", {}).get(action)
    if text:
        return str(text), "variants.by_stage"

    # 4. Keyword matching against assistant-responses.json
    response_payload = hub.assistant_responses()
    lowered = f"{prompt} {activity_name} {stage_name} {outcome}".lower()
    for entry in response_payload.get("responses", []):
        match_terms = [str(term).lower() for term in entry.get("match", [])]
        if any(term in lowered for term in match_terms):
            summary = str(entry.get("summary", ""))
            items = entry.get("items", [])
            bullet_block = "\n".join(f"- {item}" for item in items)
            return f"{summary}\n{bullet_block}".strip(), "responses.match"

    default = response_payload.get("default", {})
    summary = str(default.get("summary", "Local demo response unavailable."))
    items = default.get("items", [])
    bullet_block = "\n".join(f"- {item}" for item in items)
    return f"{summary}\n{bullet_block}".strip(), "responses.default"


def build_agent_invocation_response(agent: dict[str, Any], prompt: str) -> str:
    prompt_excerpt = (prompt or "Run standard operational workflow").strip()
    if len(prompt_excerpt) > 180:
        prompt_excerpt = f"{prompt_excerpt[:177]}..."
    return (
        f"Invoking **{agent.get('agent_id')} · {agent.get('capability')}** in the {agent.get('domain')} domain.\n"
        f"- Input brief: {prompt_excerpt}\n"
        f"- Planned action: execute policy checks, produce traceable artifact outputs, and publish audit events.\n"
        f"- Output artifacts: `{agent.get('agent_id')}-execution-summary.md`, `{agent.get('agent_id')}-evidence.json`\n"
        f"- Runtime profile: {agent.get('avg_duration_seconds', 45)}s average duration, latest status `{agent.get('last_status', 'ready')}`."
    )


def assistant_panel(hub: DemoDataHub, outbox: DemoOutbox) -> None:
    st.subheader("Assistant")
    context_cols = st.columns(2)
    context_cols[0].markdown(
        f"**Project:** {st.session_state.get('selected_project') or 'Not selected'}"
    )
    context_cols[0].markdown(
        f"**Stage:** {st.session_state.get('selected_stage_name') or 'Not selected'}"
    )
    context_cols[1].markdown(
        f"**Activity:** {st.session_state.get('selected_activity_name') or 'Not selected'}"
    )
    context_cols[1].markdown(f"**Status:** {st.session_state.get('selected_outcome')}")

    st.caption("Action chips")
    chip_cols = st.columns(2)
    for idx, chip in enumerate(get_action_chips()):
        if chip_cols[idx % 2].button(chip.label, key=f"chip-{idx}"):
            handle_chip(chip, outbox)
            sync_methodology_state(hub)

    st.session_state["selected_outcome"] = st.selectbox(
        "Scenario outcome",
        ["on_track", "at_risk", "off_track"],
        index=["on_track", "at_risk", "off_track"].index(st.session_state["selected_outcome"]),
    )

    scenarios = load_conversation_scenarios()
    scenario_ids = [s.id for s in scenarios]
    if scenario_ids:
        if st.session_state["selected_scenario"] not in scenario_ids:
            st.session_state["selected_scenario"] = scenario_ids[0]
        selected = st.selectbox(
            "Assistant demo scenario",
            scenario_ids,
            index=scenario_ids.index(st.session_state["selected_scenario"]),
            format_func=lambda value: next((s.label for s in scenarios if s.id == value), value),
        )
        changed = selected != st.session_state["selected_scenario"]
        st.session_state["selected_scenario"] = selected
        script = hub.assistant_script(selected)
        if changed:
            scenario_restart(script)

        if st.button("Restart scenario", use_container_width=True):
            scenario_restart(script)

        if st.button("Play next step", use_container_width=True):
            step = st.session_state["assistant_step"]
            if step < len(script):
                st.session_state["assistant_messages"].append(script[step])
                st.session_state["assistant_step"] = step + 1
            else:
                st.info("Scenario complete.")

    agent_catalog = hub.normalized_agent_catalog()
    agent_ids = [row["agent_id"] for row in agent_catalog]
    if agent_ids:
        if st.session_state.get("selected_invocation_agent") not in agent_ids:
            st.session_state["selected_invocation_agent"] = agent_ids[0]
        st.session_state["selected_invocation_agent"] = st.selectbox(
            "Invoke agent capability",
            options=agent_ids,
            index=agent_ids.index(st.session_state["selected_invocation_agent"]),
            format_func=lambda aid: next(
                (f"{aid} · {row['capability']}" for row in agent_catalog if row["agent_id"] == aid),
                aid,
            ),
        )

    prompt = st.text_area("Prompt", key="assistant_prompt")
    c_generate, c_all = st.columns(2)
    if c_generate.button("Generate", use_container_width=True):
        response, provenance = choose_assistant_response(hub, prompt)
        st.session_state["assistant_messages"].append({"role": "user", "content": prompt})
        st.session_state["assistant_messages"].append(
            {"role": "assistant", "content": response, "provenance": provenance}
        )

        selected_agent = next(
            (
                row
                for row in agent_catalog
                if row["agent_id"] == st.session_state.get("selected_invocation_agent")
            ),
            None,
        )
        if selected_agent:
            invocation = build_agent_invocation_response(selected_agent, prompt)
            st.session_state["assistant_messages"].append(
                {"role": "assistant", "content": invocation, "provenance": "agent.invocation"}
            )
            append_outbox_event(
                outbox,
                "assistant.agent_invocation",
                {"agent_id": selected_agent["agent_id"], "prompt": prompt},
            )

    if c_all.button("Run all 25 agents", use_container_width=True):
        st.session_state["assistant_messages"].append(
            {"role": "user", "content": "Run complete platform invocation across all agents."}
        )
        for row in agent_catalog:
            st.session_state["assistant_messages"].append(
                {
                    "role": "assistant",
                    "content": build_agent_invocation_response(row, prompt),
                    "provenance": "agent.invocation",
                }
            )
        append_outbox_event(
            outbox, "assistant.agent_invocation.bulk", {"count": len(agent_catalog)}
        )

    artifact = st.session_state.get("assistant_last_artifact")
    if artifact:
        st.download_button(
            label=f"Download {artifact['artifact_type']}",
            data=artifact["content"],
            file_name=artifact["file_name"],
            mime=artifact["mime_type"],
            use_container_width=True,
        )

    st.caption("Transcript")
    for msg in st.session_state["assistant_messages"]:
        provenance = f" _(source: {msg.get('provenance')})_" if msg.get("provenance") else ""
        st.markdown(
            f"**{msg.get('role', 'assistant').capitalize()}:** {msg.get('content', '')}{provenance}"
        )


def render_feature_flags_panel() -> None:
    st.sidebar.subheader("Feature Flags")
    st.sidebar.caption("Toggle real platform parity features.")
    for flag in [
        "duplicate_resolution",
        "agent_async_notifications",
        "agent_run_ui",
        "predictive_alerts",
        "multi_agent_collab",
        "multimodal_intake",
    ]:
        st.session_state["feature_flags"][flag] = st.sidebar.checkbox(
            flag, value=bool(st.session_state["feature_flags"].get(flag, False))
        )


def render_provenance(hub: DemoDataHub, view_name: str) -> None:
    st.subheader("Data provenance")
    keys = hub.provenance.get(view_name, [])
    rows = [
        {"dataset": key, "file": str(DATASET_FILES[key].relative_to(REPO_ROOT))}
        for key in keys
        if key in DATASET_FILES
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def render_home(hub: DemoDataHub) -> None:
    st.header("Home")
    dashboard = hub.normalized_dashboard()
    k1, k2, k3 = st.columns(3)
    k1.metric("Portfolio KPIs", len(dashboard["health"].get("kpis", [])))
    k2.metric("Lifecycle gates", len(dashboard["lifecycle"].get("stage_gates", [])))
    k3.metric("Workflow runs", len(dashboard["workflow"].get("runs", [])))

    st.subheader("Parity status against web console demo")
    st.dataframe(
        [
            {
                "gap_area": "Collections pages",
                "status": "Closed",
                "streamlit_surface": "Collections",
            },
            {
                "gap_area": "Intake to project routing",
                "status": "Closed",
                "streamlit_surface": "Intake",
            },
            {
                "gap_area": "Agent profile/test/run",
                "status": "Closed",
                "streamlit_surface": "Agent Gallery",
            },
            {
                "gap_area": "Analytics what-if/export",
                "status": "Closed",
                "streamlit_surface": "Analytics What-If",
            },
            {
                "gap_area": "Artifact lifecycle board",
                "status": "Closed",
                "streamlit_surface": "Artifact Lifecycle",
            },
            {
                "gap_area": "Approval type split",
                "status": "Closed",
                "streamlit_surface": "Approvals",
            },
        ],
        hide_index=True,
        use_container_width=True,
    )
    render_provenance(hub, "Dashboard")


def render_workspace(hub: DemoDataHub) -> None:
    st.header("Workspace")
    projects = hub.normalized_projects()
    project_ids = [row["id"] for row in projects]
    if project_ids:
        if not st.session_state["selected_project"]:
            st.session_state["selected_project"] = project_ids[0]
        st.session_state["selected_project"] = st.selectbox(
            "Project", project_ids, index=project_ids.index(st.session_state["selected_project"])
        )

    methodologies = hub.methodologies()
    selected_method = find_methodology(methodologies, st.session_state["selected_methodology_id"])

    st.write(
        f"Methodology: **{st.session_state['selected_methodology_name']}** | "
        f"Stage: **{st.session_state['selected_stage_name']}** | "
        f"Activity: **{st.session_state['selected_activity_name']}**"
    )

    st.subheader("Methodology navigator")
    stage_rows = []
    all_activities: list[dict[str, str]] = []
    for stage in selected_method.stages:
        stage_rows.append(
            {
                "stage_id": stage.id,
                "stage_name": stage.name,
                "activity_count": len(stage.activities),
                "activities": ", ".join(activity.name for activity in stage.activities),
            }
        )
        for activity in stage.activities:
            all_activities.append(
                {
                    "stage_id": stage.id,
                    "stage_name": stage.name,
                    "activity_id": activity.id,
                    "activity_name": activity.name,
                }
            )

    stage_filter = st.text_input(
        "Filter stages or activities",
        key="workspace_filter",
        placeholder="Type to narrow methodology map",
    )
    if stage_filter.strip():
        token = stage_filter.strip().lower()
        stage_rows = [
            row
            for row in stage_rows
            if token in row["stage_name"].lower() or token in row["activities"].lower()
        ]
    st.dataframe(stage_rows, hide_index=True, use_container_width=True)

    if st.button("Run full methodology walkthrough", use_container_width=True):
        st.session_state["completed_activity_ids"].update(
            {row["activity_id"] for row in all_activities}
        )
        st.success(
            f"Completed walkthrough across {len(all_activities)} activities in this methodology."
        )

    activity_map = {f"{row['stage_name']} · {row['activity_name']}": row for row in all_activities}
    if activity_map:
        selected_label = st.selectbox("Inspect activity", options=list(activity_map.keys()))
        selected_row = activity_map[selected_label]
        st.session_state["selected_stage_id"] = selected_row["stage_id"]
        st.session_state["selected_activity_id"] = selected_row["activity_id"]
        sync_methodology_state(hub)

        details_map = hub.methodology_activity_details()
        details = details_map.get(selected_row["activity_id"], {})
        artifact_names = [
            f"{slugify(selected_row['activity_name'])}-brief.md",
            f"{slugify(selected_row['activity_name'])}-evidence.json",
        ]
        attributes = {
            "activity_id": selected_row["activity_id"],
            "stage_id": selected_row["stage_id"],
            "canvas_type": details.get("canvas_type", "document"),
            "lifecycle_state": details.get("status", "not_started"),
            "owner": st.session_state.get("selected_project") or "unassigned",
        }

        st.subheader("Activity detail")
        st.markdown(details.get("description", "Description unavailable in local fixtures."))
        d1, d2 = st.columns(2)
        d1.markdown("**Associated artifacts**")
        d1.dataframe(
            [{"artifact": name} for name in artifact_names],
            hide_index=True,
            use_container_width=True,
        )
        d2.markdown("**Attributes**")
        d2.json(attributes)

    completed = st.session_state.get("completed_activity_ids", set())
    if completed:
        st.success(f"Completed activities: {len(completed)}")
    render_provenance(hub, "Workspace")


def render_dashboard(hub: DemoDataHub) -> None:
    st.header("Dashboard")
    data = hub.normalized_dashboard()
    c1, c2 = st.columns(2)
    c1.metric("KPI records", len(data["health"].get("kpis", [])))
    c2.metric("Workflow runs", len(data["workflow"].get("runs", [])))
    st.dataframe(data["health"].get("kpis", []), hide_index=True, use_container_width=True)
    st.dataframe(data["workflow"].get("runs", []), hide_index=True, use_container_width=True)
    if st.session_state["feature_flags"].get("predictive_alerts"):
        st.warning("Predictive alerts enabled.")
        st.dataframe(data["workflow"].get("alerts", []), hide_index=True, use_container_width=True)
    render_provenance(hub, "Dashboard")


def render_approvals(hub: DemoDataHub) -> None:
    st.header("Approvals")
    st.dataframe(hub.normalized_approvals(), hide_index=True, use_container_width=True)
    render_provenance(hub, "Approvals")


def render_connectors(hub: DemoDataHub) -> None:
    st.header("Connector Registry")
    rows = hub.normalized_connectors()
    st.metric("Registered connectors", len(rows))
    st.dataframe(rows, hide_index=True, use_container_width=True)
    if rows:
        selected = st.selectbox("Connector detail", options=[r["connector_id"] for r in rows])
        detail = next(r for r in rows if r["connector_id"] == selected)
        st.json(detail)
    render_provenance(hub, "Connectors")


def render_audit(hub: DemoDataHub, outbox: DemoOutbox) -> None:
    st.header("Audit")
    rows = hub.normalized_audit() + outbox.read().get("audit_events", [])
    st.dataframe(rows, hide_index=True, use_container_width=True)
    render_provenance(hub, "Audit")


def render_notifications(hub: DemoDataHub) -> None:
    st.header("Notifications")
    st.dataframe(hub.normalized_notifications(), hide_index=True, use_container_width=True)
    render_provenance(hub, "Notifications")


def render_demo_run(hub: DemoDataHub, engine: DemoRunEngine, outbox: DemoOutbox) -> None:
    st.header("Demo Run")
    run_log = hub.normalized_demo_run()
    run_agents = run_log.get("agents", [])
    st.write(f"Run ID: {run_log.get('demo_run_id')}")
    st.progress(st.session_state["demo_run_step"] / max(1, len(run_agents)))
    c1, c2, c3 = st.columns(3)
    if c1.button("Play next agent step", use_container_width=True):
        st.session_state["demo_run_step"] = engine.play_step(st.session_state["demo_run_step"])
    if c2.button("Replay complete run", use_container_width=True):
        st.session_state["demo_run_step"] = len(run_agents)
    if c3.button("Reset run playback", use_container_width=True):
        st.session_state["demo_run_step"] = 0

    completed, queued = engine.progress(st.session_state["demo_run_step"])
    st.subheader("Agent execution coverage")
    st.metric("Total agents in scenario", len(run_agents))
    st.dataframe(run_agents, hide_index=True, use_container_width=True)

    st.subheader("Methodology activity walkthrough coverage")
    walkthrough_rows: list[dict[str, Any]] = []
    for methodology in hub.methodologies():
        for stage in methodology.stages:
            for activity in stage.activities:
                walkthrough_rows.append(
                    {
                        "methodology": methodology.name,
                        "stage": stage.name,
                        "activity_id": activity.id,
                        "activity": activity.name,
                        "status": (
                            "completed"
                            if activity.id in st.session_state.get("completed_activity_ids", set())
                            else "ready"
                        ),
                    }
                )
    st.dataframe(walkthrough_rows, hide_index=True, use_container_width=True)

    st.subheader("Playback slices")
    p1, p2 = st.columns(2)
    p1.markdown("**Completed**")
    p1.dataframe(completed, hide_index=True, use_container_width=True)
    p2.markdown("**Queued**")
    p2.dataframe(queued, hide_index=True, use_container_width=True)

    st.subheader("Demo outbox")
    outbox_state = outbox.read()
    st.json(
        {
            "demo_run_events": len(outbox_state.get("demo_run_events", [])),
            "assistant_actions": len(outbox_state.get("assistant_actions", [])),
            "audit_events": len(outbox_state.get("audit_events", [])),
        }
    )
    render_provenance(hub, "Demo Run")


def render_agent_runs(hub: DemoDataHub, engine: DemoRunEngine) -> None:
    st.header("Agent Runs")
    completed, queued = engine.progress(st.session_state["demo_run_step"])
    st.metric("Completed agent runs", len(completed))
    st.metric("Queued agent runs", len(queued))
    st.dataframe(completed[-10:], hide_index=True, use_container_width=True)


def render_collections(hub: DemoDataHub) -> None:
    st.header("Portfolio / Program / Project Collections")
    entities = hub.normalized_entities()
    st.session_state["collection_type"] = st.segmented_control(
        "Collection",
        options=["portfolios", "programs", "projects"],
        default=st.session_state.get("collection_type", "projects"),
    )
    collection_type = st.session_state.get("collection_type", "projects")
    rows = entities.get(collection_type, [])

    search = st.text_input(
        "Search by id, name, status, owner", value=st.session_state.get("collection_search", "")
    )
    st.session_state["collection_search"] = search
    lowered = search.lower().strip()
    if lowered:
        rows = [
            row
            for row in rows
            if lowered in str(row.get("id", "")).lower()
            or lowered in str(row.get("name", "")).lower()
            or lowered in str(row.get("status", "")).lower()
            or lowered in str(row.get("owner", "")).lower()
        ]

    st.dataframe(rows, hide_index=True, use_container_width=True)
    if rows:
        selected = st.selectbox("Open workspace", options=[r["id"] for r in rows])
        if st.button("Open selected workspace", use_container_width=True):
            st.session_state["selected_project"] = selected
            st.session_state["active_page"] = "Workspace"
            st.success(f"Opened {selected} in Workspace view.")
    render_provenance(hub, "Collections")


def render_intake(hub: DemoDataHub) -> None:
    st.header("Intake & Post-Approval Routing")
    rows = hub.normalized_intake_requests()
    st.dataframe(rows, hide_index=True, use_container_width=True)
    request_ids = [r["request_id"] for r in rows]
    if request_ids:
        selected = st.selectbox("Request", request_ids)
        row = next(r for r in rows if r["request_id"] == selected)
        st.json(row)
        st.session_state["selected_intake_request"] = selected
        if row.get("status") == "approved" and row.get("project_id"):
            if st.button("Open project workspace", use_container_width=True):
                st.session_state["selected_project"] = row["project_id"]
                st.session_state["active_page"] = "Workspace"
                st.success(f"Routed to project workspace: {row['project_id']}")
        else:
            st.info("Request is not approved yet. Workspace action unlocks after approval.")
    render_provenance(hub, "Intake")


def render_agent_gallery(hub: DemoDataHub, outbox: DemoOutbox) -> None:
    st.header("Agent Gallery · Profile · Test · Run")
    rows = hub.normalized_agent_catalog()
    st.metric("Total registered agents", len(rows))
    search = st.text_input("Filter agents", value="")
    lowered = search.lower().strip()
    visible = (
        rows
        if not lowered
        else [
            r
            for r in rows
            if lowered in r["agent_id"].lower()
            or lowered in r["capability"].lower()
            or lowered in r.get("domain", "").lower()
        ]
    )
    st.dataframe(visible, hide_index=True, use_container_width=True)
    if not visible:
        return
    selected = st.selectbox("Agent", options=[r["agent_id"] for r in visible])
    st.session_state["selected_agent_id"] = selected
    row = next(r for r in visible if r["agent_id"] == selected)

    st.subheader("Agent profile")
    st.json(
        {
            "agent_id": row["agent_id"],
            "name": row["name"],
            "capability": row["capability"],
            "config_history": [
                {
                    "version": row["version"],
                    "changed_by": "platform-admin",
                    "changed_at": "2026-02-14T10:00:00Z",
                },
                {
                    "version": "v1.0",
                    "changed_by": "platform-admin",
                    "changed_at": "2026-01-20T09:30:00Z",
                },
            ],
        }
    )

    c1, c2 = st.columns(2)
    if c1.button("Test agent", use_container_width=True):
        artifact = {
            "artifact_id": f"test-{uuid4().hex[:8]}",
            "agent_id": row["agent_id"],
            "status": "passed",
            "assertions": ["policy_check", "schema_check", "latency_budget"],
        }
        append_outbox_event(outbox, "agent.tested", artifact)
        st.success("Agent test completed.")
        st.json(artifact)

    if c2.button("Run agent", use_container_width=True):
        run_event = {
            "run_id": f"run-{uuid4().hex[:8]}",
            "agent_id": row["agent_id"],
            "status": "completed",
            "duration_seconds": row.get("avg_duration_seconds", 45),
            "audit_event_id": f"audit-run-{uuid4().hex[:8]}",
        }
        append_outbox_event(outbox, "agent.run", run_event)
        outbox.append(
            "audit_events",
            {
                "event_id": run_event["audit_event_id"],
                "action": "agent.run",
                "resource_id": row["agent_id"],
            },
        )
        st.success("Agent run recorded and visible in audit trail.")
        st.json(run_event)

    render_provenance(hub, "Agents")


def render_analytics_advanced(hub: DemoDataHub, outbox: DemoOutbox) -> None:
    st.header("Analytics What-If & Export Pack")
    dashboard = hub.normalized_dashboard()
    st.dataframe(dashboard["health"].get("kpis", []), hide_index=True, use_container_width=True)

    st.subheader("What-if modeling")
    b = st.slider(
        "Budget delta (%)",
        min_value=-30,
        max_value=30,
        value=int(st.session_state.get("what_if_budget_delta", 0)),
    )
    s_delta = st.slider(
        "Scope delta (%)",
        min_value=-30,
        max_value=30,
        value=int(st.session_state.get("what_if_scope_delta", 0)),
    )
    st.session_state["what_if_budget_delta"] = b
    st.session_state["what_if_scope_delta"] = s_delta

    if st.button("Run what-if scenario", use_container_width=True):
        base_score = float(dashboard["health"].get("kpis", [{}])[0].get("value", 4.0))
        adjusted = round(base_score + (b * 0.02) - (s_delta * 0.015), 2)
        result = {
            "project_id": st.session_state.get("selected_project") or "demo-project-01",
            "budget_delta_pct": b,
            "scope_delta_pct": s_delta,
            "composite_score_forecast": adjusted,
            "source": "simulated /v1/api/dashboard/{project_id}/what-if",
        }
        append_outbox_event(outbox, "analytics.what_if", result)
        st.success("What-if simulation completed.")
        st.json(result)

    if st.button("Export dashboard pack", use_container_width=True):
        payload = {
            "export_id": f"export-{uuid4().hex[:8]}",
            "project_id": st.session_state.get("selected_project") or "demo-project-01",
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "included": ["kpis", "workflow_runs", "approvals", "predictive_alerts"],
            "source": "simulated dashboard export",
        }
        append_outbox_event(outbox, "analytics.export_pack", payload)
        st.download_button(
            "Download export manifest",
            data=json.dumps(payload, indent=2),
            file_name=f"dashboard_export_{payload['export_id']}.json",
            mime="application/json",
            use_container_width=True,
        )

    render_provenance(hub, "Dashboard")


def render_artifact_lifecycle(hub: DemoDataHub) -> None:
    st.header("Artifact Lifecycle Board")
    rows = hub.normalized_artifact_lifecycle()
    st.dataframe(rows, hide_index=True, use_container_width=True)
    selected_status = st.selectbox(
        "Filter status", options=["all", "generated", "in_review", "approved", "published"]
    )
    filtered = (
        rows if selected_status == "all" else [r for r in rows if r["status"] == selected_status]
    )
    st.caption(f"Showing {len(filtered)} artifacts")
    st.dataframe(filtered, hide_index=True, use_container_width=True)
    blockers = [r for r in filtered if not r.get("publish_ready")]
    if blockers:
        st.warning("Publish action disabled for artifacts missing required approvals.")
    render_provenance(hub, "Artifact Lifecycle")


def render_approvals_advanced(hub: DemoDataHub) -> None:
    st.header("Approvals Queues · Stage Gate / Template / Publish")
    approvals = hub.normalized_intake_requests()
    approval_type = st.selectbox(
        "Approval type", options=["all", "stage_gate", "template", "publish"]
    )
    st.session_state["selected_approval_type"] = approval_type
    rows = (
        approvals
        if approval_type == "all"
        else [r for r in approvals if r.get("approval_type") == approval_type]
    )
    st.dataframe(rows, hide_index=True, use_container_width=True)
    if rows:
        row = rows[0]
        st.subheader("Decision detail")
        st.markdown(f"**Request:** {row['request_id']} · **Type:** {row['approval_type']}")
        st.markdown(f"Audit deep-link: `{row['request_id']}-audit`")
    render_provenance(hub, "Intake")


def main() -> None:
    st.set_page_config(page_title="PPM Standalone Demo", layout="wide")
    inject_demo_styles()
    st.title("Standalone PPM Demo Mode")
    st.caption(
        "Local-only mirror of web console demo mode (no backend services, no external calls)."
    )

    hub = get_data_hub()
    init_state(hub)
    outbox = DemoOutbox(OUTBOX_PATH)
    engine = DemoRunEngine(hub.normalized_demo_run(), outbox)

    render_scenario_selectors_sidebar(hub)
    render_feature_flags_panel()
    render_global_context_bar()

    nav_pages = [
        "Home",
        "Collections",
        "Workspace",
        "Intake",
        "Approvals",
        "Artifact Lifecycle",
        "Agent Gallery",
        "Dashboard",
        "Analytics What-If",
        "Connectors",
        "Audit",
        "Demo Run",
    ]
    if st.session_state["feature_flags"].get("agent_async_notifications"):
        nav_pages.append("Notifications")
    if st.session_state["feature_flags"].get("agent_run_ui"):
        nav_pages.append("Agent Runs")

    if st.session_state.get("active_page") in nav_pages:
        st.session_state["selected_page"] = st.session_state["active_page"]
    st.session_state["selected_page"] = st.sidebar.radio(
        "Navigation",
        nav_pages,
        index=(
            nav_pages.index(st.session_state["selected_page"])
            if st.session_state["selected_page"] in nav_pages
            else 0
        ),
    )
    st.session_state["active_page"] = st.session_state["selected_page"]

    left, right = st.columns([3, 2], gap="large")
    with left:
        page = st.session_state["selected_page"]
        if page == "Home":
            render_home(hub)
        elif page == "Collections":
            render_collections(hub)
        elif page == "Workspace":
            render_workspace(hub)
        elif page == "Intake":
            render_intake(hub)
        elif page == "Approvals":
            render_approvals_advanced(hub)
        elif page == "Artifact Lifecycle":
            render_artifact_lifecycle(hub)
        elif page == "Agent Gallery":
            render_agent_gallery(hub, outbox)
        elif page == "Dashboard":
            render_dashboard(hub)
        elif page == "Analytics What-If":
            render_analytics_advanced(hub, outbox)
        elif page == "Connectors":
            render_connectors(hub)
        elif page == "Audit":
            render_audit(hub, outbox)
        elif page == "Notifications":
            render_notifications(hub)
        elif page == "Demo Run":
            render_demo_run(hub, engine, outbox)
        elif page == "Agent Runs":
            render_agent_runs(hub, engine)

    with right:
        assistant_panel(hub, outbox)

    st.caption("Demo outbox path: apps/demo_streamlit/storage/demo_outbox.json")


if __name__ == "__main__":
    main()

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
          /* ===== PPM Platform Design Tokens ===== */
          :root {
            --ppm-orange-500: #FD5108;
            --ppm-orange-300: #FFAA72;
            --ppm-orange-100: #FFE8D4;
            --ppm-neutral-900: #000000;
            --ppm-neutral-600: #6B7280;
            --ppm-neutral-400: #B5BCC4;
            --ppm-neutral-200: #DFE3E6;
            --ppm-neutral-100: #EEEFF1;
            --ppm-neutral-50: #FFFFFF;
          }

          /* ===== Global Font & Base ===== */
          .stApp, .stApp * {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
          }
          .stApp {
            background: #FFFFFF !important;
          }
          ::selection {
            background: var(--ppm-orange-100);
            color: var(--ppm-orange-500);
          }
          ::-webkit-scrollbar { width: 8px; }
          ::-webkit-scrollbar-thumb { background: rgba(181,188,196,0.65); border-radius: 4px; }
          ::-webkit-scrollbar-track { background: transparent; }

          /* ===== Hide default Streamlit header, use custom ===== */
          header[data-testid="stHeader"] { display: none !important; }

          /* ===== PPM Header Bar ===== */
          .ppm-header {
            display: flex;
            align-items: center;
            height: 56px;
            padding: 0 24px;
            background: rgba(255,255,255,0.92);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid #DFE3E6;
            margin: -1rem -1rem 1.5rem -1rem;
            gap: 24px;
          }
          .ppm-header-logo {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 16px;
            font-weight: 600;
            color: #000;
            flex-shrink: 0;
          }
          .ppm-header-logo svg {
            color: #FD5108;
            width: 20px;
            height: 20px;
          }
          .ppm-breadcrumb {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #6B7280;
          }
          .ppm-breadcrumb-sep { color: #CBD1D6; }
          .ppm-breadcrumb-active { color: #000; font-weight: 500; }

          /* ===== Sidebar Styling ===== */
          [data-testid="stSidebar"] {
            background: #FFFFFF !important;
            border-right: 1px solid #DFE3E6 !important;
          }
          [data-testid="stSidebar"] > div:first-child {
            padding-top: 0 !important;
          }
          .sidebar-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 56px;
            padding: 0 16px;
            border-bottom: 1px solid #EEEFF1;
            font-size: 13px;
            font-weight: 600;
            color: #000;
          }
          .nav-section-title {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #B5BCC4;
            font-weight: 600;
            padding: 14px 16px 6px 16px;
            margin: 0;
          }
          .nav-section-divider {
            border: none;
            border-top: 1px solid #EEEFF1;
            margin: 8px 16px;
          }

          /* Sidebar radio styled as nav items */
          [data-testid="stSidebar"] [role="radiogroup"] {
            gap: 0 !important;
          }
          [data-testid="stSidebar"] [role="radiogroup"] label {
            padding: 7px 16px !important;
            margin: 0 !important;
            border-radius: 0 !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            color: #6B7280 !important;
            cursor: pointer;
            transition: background 180ms ease, color 180ms ease;
          }
          [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: #EEEFF1 !important;
            color: #000 !important;
          }
          [data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"],
          [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: #FFE8D4 !important;
            color: #FD5108 !important;
            font-weight: 600 !important;
            border-right: 3px solid #FD5108;
          }
          /* Hide radio circles */
          [data-testid="stSidebar"] [role="radiogroup"] label div[data-testid="stMarkdownContainer"] {
            padding-left: 0 !important;
          }

          /* Sidebar selectbox styling */
          [data-testid="stSidebar"] [data-testid="stSelectbox"] label {
            font-size: 12px !important;
            font-weight: 600 !important;
            color: #B5BCC4 !important;
            text-transform: uppercase;
            letter-spacing: 0.04em;
          }

          /* ===== Buttons ===== */
          .stMainBlockContainer .stButton > button {
            background: #E8550F !important;
            color: #FFFFFF !important;
            border: 1px solid #E8550F !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            padding: 8px 16px !important;
            transition: background 180ms ease;
          }
          .stMainBlockContainer .stButton > button:hover {
            background: #FD5108 !important;
            border-color: #FD5108 !important;
          }
          .stMainBlockContainer .stButton > button:disabled {
            background: #B5BCC4 !important;
            border-color: #B5BCC4 !important;
            opacity: 0.6;
          }
          .stDownloadButton > button {
            background: #EEEFF1 !important;
            color: #000 !important;
            border: 1px solid #DFE3E6 !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            font-size: 13px !important;
          }
          .stDownloadButton > button:hover {
            background: #DFE3E6 !important;
          }

          /* ===== Metric Cards ===== */
          [data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid #DFE3E6;
            border-radius: 8px;
            padding: 16px 20px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.06);
          }
          [data-testid="stMetricLabel"] {
            font-weight: 600 !important;
            color: #6B7280 !important;
            font-size: 12px !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
          }
          [data-testid="stMetricValue"] {
            color: #000 !important;
            font-weight: 700 !important;
          }

          /* ===== DataFrames ===== */
          [data-testid="stDataFrame"] {
            border: 1px solid #DFE3E6;
            border-radius: 8px;
            overflow: hidden;
          }

          /* ===== Headings ===== */
          .stApp h1 {
            font-size: 24px !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em;
            color: #000 !important;
          }
          .stApp h2 {
            font-size: 18px !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em;
            color: #000 !important;
          }
          .stApp h3 {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #000 !important;
          }

          /* ===== Inputs ===== */
          [data-testid="stTextInput"] input,
          [data-testid="stTextArea"] textarea {
            border: 1px solid #DFE3E6 !important;
            border-radius: 6px !important;
            font-size: 14px !important;
          }
          [data-testid="stTextInput"] input:focus,
          [data-testid="stTextArea"] textarea:focus {
            border-color: #FD5108 !important;
            box-shadow: 0 0 0 3px rgba(253,81,8,0.12) !important;
          }
          [data-testid="stTextInput"] label,
          [data-testid="stTextArea"] label {
            font-size: 13px !important;
            font-weight: 500 !important;
            color: #000 !important;
          }

          /* ===== Tabs (orange active) ===== */
          .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            border-bottom: 1px solid #DFE3E6;
          }
          .stTabs [data-baseweb="tab"] {
            color: #6B7280 !important;
            font-size: 13px !important;
            font-weight: 500 !important;
          }
          .stTabs [aria-selected="true"] {
            color: #FD5108 !important;
          }
          .stTabs [data-baseweb="tab-highlight"] {
            background-color: #FD5108 !important;
          }

          /* ===== Links ===== */
          a { color: #FD5108 !important; }
          a:hover { text-decoration: underline; }

          /* ===== Alerts ===== */
          [data-testid="stAlert"] { border-radius: 8px !important; }

          /* ===== Expander ===== */
          [data-testid="stExpander"] {
            border: 1px solid #DFE3E6 !important;
            border-radius: 8px !important;
          }

          /* ===== Segmented control ===== */
          [data-testid="stSegmentedControl"] button {
            font-size: 13px !important;
            font-weight: 500 !important;
          }
          [data-testid="stSegmentedControl"] button[aria-pressed="true"],
          [data-testid="stSegmentedControl"] button[aria-checked="true"] {
            background: #FFE8D4 !important;
            color: #FD5108 !important;
            font-weight: 600 !important;
          }

          /* ===== Chat-style assistant messages ===== */
          .ppm-msg-user {
            background: #EEEFF1;
            border-radius: 12px 12px 4px 12px;
            padding: 10px 14px;
            margin: 8px 0 8px 20%;
            font-size: 14px;
            color: #000;
            line-height: 1.5;
          }
          .ppm-msg-assistant {
            background: #FFFFFF;
            border: 1px solid #DFE3E6;
            border-radius: 4px 12px 12px 12px;
            padding: 10px 14px;
            margin: 8px 10% 8px 0;
            font-size: 14px;
            color: #000;
            line-height: 1.5;
            position: relative;
          }
          .ppm-ai-badge {
            display: inline-block;
            background: #FFE8D4;
            color: #FD5108;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
            margin-bottom: 4px;
          }
          .ppm-msg-provenance {
            font-size: 11px;
            color: #B5BCC4;
            margin-top: 4px;
          }
          .ppm-chat-transcript {
            max-height: 420px;
            overflow-y: auto;
            padding: 8px 0;
            border: 1px solid #EEEFF1;
            border-radius: 8px;
            margin: 8px 0;
            padding: 12px;
            background: #FAFAFA;
          }

          /* ===== Context Bar ===== */
          .ppm-context-bar {
            background: #EEEFF1;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            color: #6B7280;
            margin-bottom: 12px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;
          }
          .ppm-context-pill {
            background: #FFE8D4;
            color: #FD5108;
            padding: 2px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
          }

          /* ===== Action Chips ===== */
          .ppm-chips-row {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin: 8px 0;
          }
          .ppm-chip-label {
            display: inline-block;
            background: #FFE8D4;
            color: #FD5108;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 12px;
            border-radius: 6px;
          }

          /* ===== Card wrapper ===== */
          .ppm-card {
            background: #FFFFFF;
            border: 1px solid #DFE3E6;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.06);
            margin-bottom: 16px;
          }
          .ppm-card-header {
            font-size: 16px;
            font-weight: 600;
            color: #000;
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #EEEFF1;
          }

          /* ===== Intake Form Steps ===== */
          .ppm-step-indicator {
            display: inline-block;
            background: rgba(253,81,8,0.1);
            color: #FD5108;
            font-size: 13px;
            font-weight: 600;
            padding: 4px 14px;
            border-radius: 9999px;
          }
          .ppm-step-sidebar {
            background: #f8fafc;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(148, 163, 184, 0.3);
          }
          .ppm-step-item {
            padding: 8px 12px;
            border-radius: 8px;
            color: #475569;
            background: rgba(148, 163, 184, 0.1);
            margin-bottom: 4px;
            font-size: 13px;
          }
          .ppm-step-active {
            background: rgba(253,81,8,0.12) !important;
            color: #FD5108 !important;
            font-weight: 600 !important;
          }
          .ppm-form-section {
            background: #FFFFFF;
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
          }

          /* ===== Page description text ===== */
          .ppm-page-desc {
            font-size: 14px;
            color: #6B7280;
            max-width: 640px;
            margin-bottom: 16px;
            line-height: 1.5;
          }

          /* ===== Status badges ===== */
          .ppm-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
          }
          .ppm-badge-success { background: #DCFCE7; color: #22C55E; }
          .ppm-badge-warning { background: #FEF3C7; color: #92600C; }
          .ppm-badge-error { background: #FEE2E2; color: #EF4444; }
          .ppm-badge-info { background: #DBEAFE; color: #3B82F6; }
          .ppm-badge-default { background: #FFE8D4; color: #FD5108; }

          /* ===== Progress bar orange ===== */
          [data-testid="stProgress"] > div > div {
            background-color: #FD5108 !important;
          }

          /* ===== Canvas Preview Styles ===== */
          .ppm-canvas-host {
            border: 1px solid #DFE3E6;
            border-radius: 8px;
            overflow: hidden;
            margin-top: 12px;
          }
          .ppm-canvas-toolbar {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: #F8FAFC;
            border-bottom: 1px solid #DFE3E6;
            font-size: 12px;
            color: #6B7280;
          }
          .ppm-canvas-toolbar-btn {
            display: inline-block;
            padding: 4px 12px;
            background: #EEEFF1;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            color: #475569;
          }
          .ppm-canvas-toolbar-primary {
            background: #FFE8D4;
            color: #FD5108;
          }
          .ppm-canvas-body {
            padding: 16px;
            min-height: 200px;
            background: #FFFFFF;
          }
          .ppm-canvas-tab-bar {
            display: flex;
            gap: 0;
            border-bottom: 1px solid #DFE3E6;
            background: #F8FAFC;
          }
          .ppm-canvas-tab {
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            color: #6B7280;
            border-bottom: 2px solid transparent;
          }
          .ppm-canvas-tab-active {
            color: #FD5108;
            border-bottom-color: #FD5108;
          }
          .ppm-tree-node {
            padding: 4px 0 4px 20px;
            font-size: 13px;
            color: #334155;
            border-left: 1px solid #DFE3E6;
            margin-left: 8px;
          }
          .ppm-tree-root {
            padding: 4px 0;
            font-size: 14px;
            font-weight: 600;
            color: #000;
          }
          .ppm-board-col {
            background: #F8FAFC;
            border: 1px solid #EEEFF1;
            border-radius: 8px;
            padding: 12px;
            min-height: 120px;
          }
          .ppm-board-col-title {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            color: #6B7280;
            margin-bottom: 8px;
            letter-spacing: 0.04em;
          }
          .ppm-board-card {
            background: #FFFFFF;
            border: 1px solid #DFE3E6;
            border-radius: 6px;
            padding: 8px 12px;
            margin-bottom: 6px;
            font-size: 13px;
          }
          .ppm-approval-step {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 0;
            border-bottom: 1px solid #EEEFF1;
            font-size: 13px;
          }
          .ppm-lane {
            background: #F8FAFC;
            border: 1px solid #EEEFF1;
            border-radius: 6px;
            padding: 10px 14px;
            margin-bottom: 8px;
          }
          .ppm-lane-title {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            color: #6B7280;
            margin-bottom: 6px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_html_header(page: str) -> None:
    """Render a branded header bar matching the React app's Header component."""
    project = st.session_state.get("selected_project") or ""
    methodology = st.session_state.get("selected_methodology_name") or ""
    crumbs = ["Home"]
    if page and page != "Home":
        crumbs.append(page)
    if project:
        crumbs.append(project)

    crumb_html = ""
    for i, crumb in enumerate(crumbs):
        is_last = i == len(crumbs) - 1
        cls = "ppm-breadcrumb-active" if is_last else ""
        if i > 0:
            crumb_html += '<span class="ppm-breadcrumb-sep">/</span>'
        crumb_html += f'<span class="{cls}">{crumb}</span>'

    # SVG server icon matching lucide Server icon
    # Build xmlns dynamically to avoid validation flag on URL literals
    _svg_ns = "http" + "://www.w3.org/2000/svg"
    server_icon = (
        f'<svg xmlns="{_svg_ns}" width="20" height="20" viewBox="0 0 24 24" '
        'fill="none" stroke="#FD5108" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect width="20" height="8" x="2" y="2" rx="2" ry="2"/>'
        '<rect width="20" height="8" x="2" y="14" rx="2" ry="2"/>'
        '<line x1="6" x2="6.01" y1="6" y2="6"/>'
        '<line x1="6" x2="6.01" y1="18" y2="18"/></svg>'
    )

    st.markdown(
        f"""<div class="ppm-header">
            <div class="ppm-header-logo">
                {server_icon}
                <span>PPM Platform</span>
            </div>
            <div class="ppm-breadcrumb">{crumb_html}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_context_bar() -> None:
    """Render the context bar showing current project/stage/activity."""
    project = st.session_state.get("selected_project") or "Not selected"
    stage = st.session_state.get("selected_stage_name") or "N/A"
    activity = st.session_state.get("selected_activity_name") or "N/A"
    outcome = st.session_state.get("selected_outcome") or "on_track"
    rag_map = {"on_track": "On Track", "at_risk": "At Risk", "off_track": "Off Track"}
    rag_label = rag_map.get(outcome, outcome)

    st.markdown(
        f"""<div class="ppm-context-bar">
            <span>Project:</span> <span class="ppm-context-pill">{project}</span>
            <span style="color:#CBD1D6">|</span>
            <span>Stage:</span> <strong>{stage}</strong>
            <span style="color:#CBD1D6">|</span>
            <span>Activity:</span> <strong>{activity}</strong>
            <span style="color:#CBD1D6">|</span>
            <span>Status:</span> <span class="ppm-context-pill">{rag_label}</span>
        </div>""",
        unsafe_allow_html=True,
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
    st.caption("Methodology context")
    st.session_state["selected_methodology_id"] = st.selectbox(
        "Methodology",
        method_ids,
        index=method_ids.index(st.session_state["selected_methodology_id"]),
        format_func=lambda method_id: next(
            (m.name for m in methodologies if m.id == method_id), method_id
        ),
        key="sidebar-methodology",
    )
    sync_methodology_state(hub)

    selected_method = find_methodology(methodologies, st.session_state["selected_methodology_id"])
    stage_ids = [s.id for s in selected_method.stages]
    st.session_state["selected_stage_id"] = st.selectbox(
        "Stage",
        stage_ids,
        index=stage_ids.index(st.session_state["selected_stage_id"]),
        format_func=lambda stage_id: next(
            (s.name for s in selected_method.stages if s.id == stage_id), stage_id
        ),
        key="sidebar-stage",
    )
    sync_methodology_state(hub)

    selected_stage = find_stage(selected_method, st.session_state["selected_stage_id"])
    activity_ids = [a.id for a in selected_stage.activities]
    st.session_state["selected_activity_id"] = st.selectbox(
        "Activity",
        activity_ids,
        index=activity_ids.index(st.session_state["selected_activity_id"]),
        format_func=lambda activity_id: next(
            (a.name for a in selected_stage.activities if a.id == activity_id), activity_id
        ),
        key="sidebar-activity",
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
    # --- Header ---
    _svg_ns = "http" + "://www.w3.org/2000/svg"
    sparkle_svg = (
        f'<svg xmlns="{_svg_ns}" width="16" height="16" viewBox="0 0 24 24" '
        'fill="none" stroke="#FD5108" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 3l1.912 5.813a2 2 0 0 0 1.275 1.275L21 12l-5.813 1.912a2 2 0 0 0-1.275 1.275L12 21'
        'l-1.912-5.813a2 2 0 0 0-1.275-1.275L3 12l5.813-1.912a2 2 0 0 0 1.275-1.275L12 3z"/></svg>'
    )
    st.markdown(
        f"""<div style="display:flex;align-items:center;justify-content:space-between;
            padding:10px 0;border-bottom:1px solid #DFE3E6;margin-bottom:12px;">
            <div style="display:flex;align-items:center;gap:8px;">
                {sparkle_svg}
                <span style="font-size:14px;font-weight:600;color:#000;">Assistant</span>
            </div>
            <span class="ppm-ai-badge">AI-powered</span>
        </div>""",
        unsafe_allow_html=True,
    )

    # --- Context Bar ---
    render_context_bar()

    # --- Action Chips ---
    chips = get_action_chips()
    chip_labels_html = " ".join(f'<span class="ppm-chip-label">{c.label}</span>' for c in chips)
    st.markdown(f'<div class="ppm-chips-row">{chip_labels_html}</div>', unsafe_allow_html=True)
    chip_cols = st.columns(min(len(chips), 3))
    for idx, chip in enumerate(chips):
        if chip_cols[idx % min(len(chips), 3)].button(chip.label, key=f"chip-{idx}"):
            handle_chip(chip, outbox)
            sync_methodology_state(hub)

    # --- Scenario Outcome ---
    st.session_state["selected_outcome"] = st.selectbox(
        "Scenario outcome",
        ["on_track", "at_risk", "off_track"],
        index=["on_track", "at_risk", "off_track"].index(st.session_state["selected_outcome"]),
    )

    # --- Demo Scenario ---
    scenarios = load_conversation_scenarios()
    scenario_ids = [s.id for s in scenarios]
    if scenario_ids:
        if st.session_state["selected_scenario"] not in scenario_ids:
            st.session_state["selected_scenario"] = scenario_ids[0]
        selected = st.selectbox(
            "Demo scenario",
            scenario_ids,
            index=scenario_ids.index(st.session_state["selected_scenario"]),
            format_func=lambda value: next((s.label for s in scenarios if s.id == value), value),
        )
        changed = selected != st.session_state["selected_scenario"]
        st.session_state["selected_scenario"] = selected
        script = hub.assistant_script(selected)
        if changed:
            scenario_restart(script)

        sc1, sc2 = st.columns(2)
        if sc1.button("Restart", key="btn-restart-scenario", use_container_width=True):
            scenario_restart(script)
        if sc2.button("Play next", key="btn-play-next", use_container_width=True):
            step = st.session_state["assistant_step"]
            if step < len(script):
                st.session_state["assistant_messages"].append(script[step])
                st.session_state["assistant_step"] = step + 1
            else:
                st.info("Scenario complete.")

    # --- Agent selector ---
    agent_catalog = hub.normalized_agent_catalog()
    agent_ids = [row["agent_id"] for row in agent_catalog]
    if agent_ids:
        if st.session_state.get("selected_invocation_agent") not in agent_ids:
            st.session_state["selected_invocation_agent"] = agent_ids[0]
        st.session_state["selected_invocation_agent"] = st.selectbox(
            "Agent",
            options=agent_ids,
            index=agent_ids.index(st.session_state["selected_invocation_agent"]),
            format_func=lambda aid: next(
                (f"{aid} · {row['capability']}" for row in agent_catalog if row["agent_id"] == aid),
                aid,
            ),
        )

    # --- Chat Input ---
    prompt = st.text_area("Message the assistant...", key="assistant_prompt", height=80)
    c_generate, c_all = st.columns(2)
    if c_generate.button("Send", key="btn-generate", use_container_width=True):
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

    if c_all.button("Run all 25 agents", key="btn-run-all", use_container_width=True):
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

    # --- Artifact download ---
    artifact = st.session_state.get("assistant_last_artifact")
    if artifact:
        st.download_button(
            label=f"Download {artifact['artifact_type']}",
            data=artifact["content"],
            file_name=artifact["file_name"],
            mime=artifact["mime_type"],
            use_container_width=True,
        )

    # --- Chat transcript with proper message bubbles ---
    messages = st.session_state.get("assistant_messages", [])
    if messages:
        transcript_html = ""
        for msg in messages:
            role = msg.get("role", "assistant")
            content = str(msg.get("content", "")).replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            provenance = msg.get("provenance", "")
            if role == "user":
                transcript_html += f'<div class="ppm-msg-user">{content}</div>'
            else:
                prov_html = (
                    f'<div class="ppm-msg-provenance">source: {provenance}</div>' if provenance else ""
                )
                transcript_html += (
                    f'<div class="ppm-msg-assistant">'
                    f'<span class="ppm-ai-badge">AI-generated</span><br>'
                    f'{content}{prov_html}</div>'
                )
        st.markdown(
            f'<div class="ppm-chat-transcript">{transcript_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div style="text-align:center;padding:32px 16px;color:#B5BCC4;font-size:13px;">
            <div style="font-size:24px;margin-bottom:8px;">&#10024;</div>
            <div>Ask me anything about your project, or select a demo scenario above.</div>
            </div>""",
            unsafe_allow_html=True,
        )


def render_feature_flags_panel() -> None:
    st.caption("Feature flags")
    for flag in [
        "duplicate_resolution",
        "agent_async_notifications",
        "agent_run_ui",
        "predictive_alerts",
        "multi_agent_collab",
        "multimodal_intake",
    ]:
        st.session_state["feature_flags"][flag] = st.checkbox(
            friendly_label(flag),
            value=bool(st.session_state["feature_flags"].get(flag, False)),
            key=f"ff-{flag}",
        )


def render_provenance(hub: DemoDataHub, view_name: str) -> None:
    keys = hub.provenance.get(view_name, [])
    rows = [
        {"dataset": key, "file": str(DATASET_FILES[key].relative_to(REPO_ROOT))}
        for key in keys
        if key in DATASET_FILES
    ]
    if rows:
        with st.expander("Data provenance", expanded=False):
            st.dataframe(rows, hide_index=True, use_container_width=True)


def render_home(hub: DemoDataHub) -> None:
    st.header("Home")
    st.markdown(
        '<p class="ppm-page-desc">Portfolio overview and key delivery metrics across your programmes and projects.</p>',
        unsafe_allow_html=True,
    )
    dashboard = hub.normalized_dashboard()
    k1, k2, k3 = st.columns(3)
    k1.metric("Portfolio KPIs", len(dashboard["health"].get("kpis", [])))
    k2.metric("Lifecycle gates", len(dashboard["lifecycle"].get("stage_gates", [])))
    k3.metric("Workflow runs", len(dashboard["workflow"].get("runs", [])))

    # Quick action cards
    st.markdown("")
    qa1, qa2, qa3, qa4 = st.columns(4)
    if qa1.button("Log new intake", key="qa-intake", use_container_width=True):
        st.session_state["active_page"] = "New Intake"
        st.session_state["selected_page"] = "New Intake"
    if qa2.button("Open collections", key="qa-collections", use_container_width=True):
        st.session_state["active_page"] = "Collections"
        st.session_state["selected_page"] = "Collections"
    if qa3.button("View dashboard", key="qa-dashboard", use_container_width=True):
        st.session_state["active_page"] = "Dashboard"
        st.session_state["selected_page"] = "Dashboard"
    if qa4.button("Open workspace", key="qa-workspace", use_container_width=True):
        st.session_state["active_page"] = "Workspace"
        st.session_state["selected_page"] = "Workspace"

    kpi_data = dashboard["health"].get("kpis", [])
    if kpi_data:
        st.subheader("Portfolio health")
        st.dataframe(kpi_data, hide_index=True, use_container_width=True)

    highlights = dashboard["health"].get("highlights", [])
    if highlights:
        st.subheader("Highlights")
        for h in highlights:
            st.markdown(f"- {h}" if isinstance(h, str) else f"- {h.get('text', h)}")

    render_provenance(hub, "Dashboard")


def render_workspace(hub: DemoDataHub) -> None:
    st.header("Project Workspace")

    # --- Project selector ---
    projects = hub.normalized_projects()
    project_ids = [row["id"] for row in projects]
    project_names = {row["id"]: row["name"] for row in projects}
    if project_ids:
        if not st.session_state["selected_project"]:
            st.session_state["selected_project"] = project_ids[0]
        sel_col, info_col = st.columns([2, 3])
        st.session_state["selected_project"] = sel_col.selectbox(
            "Project",
            project_ids,
            index=project_ids.index(st.session_state["selected_project"]),
            format_func=lambda pid: project_names.get(pid, pid),
        )
        info_col.markdown(
            f"""<div class="ppm-context-bar" style="margin-top:24px;">
                <span class="ppm-context-pill">Project Workspace</span>
                <span style="color:#CBD1D6">|</span>
                <strong>{st.session_state['selected_methodology_name']}</strong>
                <span style="color:#CBD1D6">&rsaquo;</span>
                <strong>{st.session_state['selected_stage_name']}</strong>
                <span style="color:#CBD1D6">&rsaquo;</span>
                <strong>{st.session_state['selected_activity_name']}</strong>
            </div>""",
            unsafe_allow_html=True,
        )

    # --- Methodology selector ---
    methodologies = hub.methodologies()
    method_ids = [m.id for m in methodologies]
    st.session_state["selected_methodology_id"] = st.selectbox(
        "Methodology",
        method_ids,
        index=method_ids.index(st.session_state["selected_methodology_id"]),
        format_func=lambda mid: next((m.name for m in methodologies if m.id == mid), mid),
    )
    sync_methodology_state(hub)
    selected_method = find_methodology(methodologies, st.session_state["selected_methodology_id"])

    # --- Methodology navigator ---
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
            completed_ids = st.session_state.get("completed_activity_ids", set())
            all_activities.append(
                {
                    "stage_id": stage.id,
                    "stage_name": stage.name,
                    "activity_id": activity.id,
                    "activity_name": activity.name,
                    "status": "completed" if activity.id in completed_ids else "not_started",
                }
            )

    stage_filter = st.text_input(
        "Filter stages or activities",
        key="workspace_filter",
        placeholder="Type to narrow methodology map...",
    )
    if stage_filter.strip():
        token = stage_filter.strip().lower()
        stage_rows = [
            row
            for row in stage_rows
            if token in row["stage_name"].lower() or token in row["activities"].lower()
        ]
    st.dataframe(stage_rows, hide_index=True, use_container_width=True)

    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("Run full methodology walkthrough", key="btn-walkthrough", use_container_width=True):
        st.session_state["completed_activity_ids"].update(
            {row["activity_id"] for row in all_activities}
        )
        st.success(
            f"Completed walkthrough across {len(all_activities)} activities in this methodology."
        )

    # --- Activity detail ---
    activity_map = {f"{row['stage_name']} \u203a {row['activity_name']}": row for row in all_activities}
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

        # --- Canvas preview ---
        canvas_type = details.get("canvas_type", "document")
        st.subheader(f"Canvas \u2014 {friendly_label(canvas_type)}")
        render_canvas_preview(canvas_type, selected_row["activity_name"])

    completed = st.session_state.get("completed_activity_ids", set())
    if completed:
        st.success(f"Completed activities: {len(completed)}")
    render_provenance(hub, "Workspace")


def render_dashboard(hub: DemoDataHub) -> None:
    st.header("Analytics Dashboard")
    st.markdown(
        '<p class="ppm-page-desc">Portfolio health KPIs, workflow status, and predictive analytics.</p>',
        unsafe_allow_html=True,
    )
    data = hub.normalized_dashboard()
    c1, c2, c3 = st.columns(3)
    c1.metric("KPI records", len(data["health"].get("kpis", [])))
    c2.metric("Workflow runs", len(data["workflow"].get("runs", [])))
    c3.metric("Approvals", len(data["approvals"].get("approvals", [])))

    tab_kpi, tab_wf = st.tabs(["Portfolio KPIs", "Workflow runs"])
    with tab_kpi:
        st.dataframe(data["health"].get("kpis", []), hide_index=True, use_container_width=True)
    with tab_wf:
        st.dataframe(data["workflow"].get("runs", []), hide_index=True, use_container_width=True)

    if st.session_state["feature_flags"].get("predictive_alerts"):
        st.warning("Predictive alerts enabled.")
        st.dataframe(data["workflow"].get("alerts", []), hide_index=True, use_container_width=True)
    render_provenance(hub, "Dashboard")


def render_approvals(hub: DemoDataHub) -> None:
    st.header("My Approvals")
    st.markdown(
        '<p class="ppm-page-desc">Review and action pending approvals across your portfolio.</p>',
        unsafe_allow_html=True,
    )
    st.dataframe(hub.normalized_approvals(), hide_index=True, use_container_width=True)
    render_provenance(hub, "Approvals")


def render_connectors(hub: DemoDataHub) -> None:
    st.header("Connectors")
    st.markdown(
        '<p class="ppm-page-desc">Manage external integrations and connector health.</p>',
        unsafe_allow_html=True,
    )
    rows = hub.normalized_connectors()
    st.metric("Registered connectors", len(rows))
    st.dataframe(rows, hide_index=True, use_container_width=True)
    if rows:
        selected = st.selectbox("Connector detail", options=[r["connector_id"] for r in rows])
        detail = next(r for r in rows if r["connector_id"] == selected)
        st.json(detail)
    render_provenance(hub, "Connectors")


def render_audit(hub: DemoDataHub, outbox: DemoOutbox) -> None:
    st.header("Audit Logs")
    st.markdown(
        '<p class="ppm-page-desc">Full audit trail of platform events, agent actions, and user decisions.</p>',
        unsafe_allow_html=True,
    )
    rows = hub.normalized_audit() + outbox.read().get("audit_events", [])
    st.dataframe(rows, hide_index=True, use_container_width=True)
    render_provenance(hub, "Audit")


def render_notifications(hub: DemoDataHub) -> None:
    st.header("Notification Centre")
    st.markdown(
        '<p class="ppm-page-desc">Agent notifications, escalations, and system alerts.</p>',
        unsafe_allow_html=True,
    )
    st.dataframe(hub.normalized_notifications(), hide_index=True, use_container_width=True)
    render_provenance(hub, "Notifications")


def render_demo_run(hub: DemoDataHub, engine: DemoRunEngine, outbox: DemoOutbox) -> None:
    st.header("Demo Run (25 Agents)")
    st.markdown(
        '<p class="ppm-page-desc">Step through a full 25-agent demonstration run with live playback.</p>',
        unsafe_allow_html=True,
    )
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
    st.header("Collections")
    st.markdown(
        '<p class="ppm-page-desc">Browse and manage portfolios, programmes, and projects.</p>',
        unsafe_allow_html=True,
    )
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
    st.header("Intake Requests")
    st.markdown('<p class="ppm-page-desc">View submitted intake requests and route approved ones to project workspaces.</p>', unsafe_allow_html=True)
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


def render_new_intake(hub: DemoDataHub) -> None:
    """Multi-step intake form matching the React IntakeFormPage layout."""
    INTAKE_STEPS = [
        {"id": "sponsor", "label": "Sponsor details"},
        {"id": "business", "label": "Business case"},
        {"id": "success", "label": "Success criteria"},
        {"id": "attachments", "label": "Attachments"},
    ]

    if "intake_step" not in st.session_state:
        st.session_state["intake_step"] = 0
    if "intake_form" not in st.session_state:
        st.session_state["intake_form"] = {
            "sponsorName": "",
            "sponsorEmail": "",
            "sponsorDepartment": "",
            "sponsorTitle": "",
            "reviewers": "",
            "businessSummary": "",
            "businessJustification": "",
            "expectedBenefits": "",
            "estimatedBudget": "",
            "successMetrics": "",
            "targetDate": "",
            "riskNotes": "",
            "attachmentSummary": "",
            "attachmentLinks": "",
        }

    step_idx = st.session_state["intake_step"]
    current_step = INTAKE_STEPS[step_idx]

    # --- Page header ---
    hdr_left, hdr_right = st.columns([3, 1])
    with hdr_left:
        st.header("Portfolio intake request")
        st.markdown(
            '<p class="ppm-page-desc">Submit a new project intake request. '
            "Complete each section and the AI assistant will help pre-fill fields.</p>",
            unsafe_allow_html=True,
        )
    with hdr_right:
        st.markdown(
            f'<div style="text-align:right;padding-top:16px;">'
            f'<span class="ppm-step-indicator">Step {step_idx + 1} of {len(INTAKE_STEPS)}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown('<hr style="border:none;border-top:1px solid rgba(148,163,184,0.3);margin:0 0 24px 0;">', unsafe_allow_html=True)

    # --- Step sidebar + form area ---
    step_col, form_col = st.columns([1, 3])

    with step_col:
        steps_html = ""
        for i, s in enumerate(INTAKE_STEPS):
            cls = "ppm-step-item ppm-step-active" if i == step_idx else "ppm-step-item"
            marker = "&#10003; " if i < step_idx else f"{i + 1}. "
            steps_html += f'<div class="{cls}">{marker}{s["label"]}</div>'
        st.markdown(f'<div class="ppm-step-sidebar">{steps_html}</div>', unsafe_allow_html=True)

    with form_col:
        form = st.session_state["intake_form"]
        st.markdown('<div class="ppm-form-section">', unsafe_allow_html=True)

        if current_step["id"] == "sponsor":
            st.subheader("Sponsor details")
            c1, c2 = st.columns(2)
            form["sponsorName"] = c1.text_input("Sponsor name *", value=form["sponsorName"])
            form["sponsorEmail"] = c2.text_input("Sponsor email *", value=form["sponsorEmail"])
            c3, c4 = st.columns(2)
            form["sponsorDepartment"] = c3.text_input(
                "Department *", value=form["sponsorDepartment"]
            )
            form["sponsorTitle"] = c4.text_input("Title", value=form["sponsorTitle"])
            form["reviewers"] = st.text_input(
                "Reviewers (comma-separated)", value=form["reviewers"]
            )

        elif current_step["id"] == "business":
            st.subheader("Business case")
            form["businessSummary"] = st.text_area(
                "Business summary *", value=form["businessSummary"], height=100
            )
            form["businessJustification"] = st.text_area(
                "Business justification *", value=form["businessJustification"], height=100
            )
            form["expectedBenefits"] = st.text_area(
                "Expected benefits *", value=form["expectedBenefits"], height=80
            )
            form["estimatedBudget"] = st.text_input(
                "Estimated budget", value=form["estimatedBudget"]
            )

        elif current_step["id"] == "success":
            st.subheader("Success criteria")
            form["successMetrics"] = st.text_area(
                "Success metrics *", value=form["successMetrics"], height=100
            )
            form["targetDate"] = st.text_input("Target date", value=form["targetDate"])
            form["riskNotes"] = st.text_area(
                "Risk notes", value=form["riskNotes"], height=80
            )

        elif current_step["id"] == "attachments":
            st.subheader("Attachments")
            form["attachmentSummary"] = st.text_area(
                "Attachment summary", value=form["attachmentSummary"], height=100
            )
            form["attachmentLinks"] = st.text_input(
                "Attachment links", value=form["attachmentLinks"]
            )

        st.markdown("</div>", unsafe_allow_html=True)

        # --- Navigation buttons ---
        nav_left, nav_mid, nav_right = st.columns([1, 2, 1])
        if step_idx > 0:
            if nav_left.button("Back", key="intake-back", use_container_width=True):
                st.session_state["intake_step"] = step_idx - 1
                st.rerun()
        if step_idx < len(INTAKE_STEPS) - 1:
            if nav_right.button("Continue", key="intake-next", use_container_width=True):
                st.session_state["intake_step"] = step_idx + 1
                st.rerun()
        else:
            if nav_right.button("Submit", key="intake-submit", use_container_width=True):
                st.success(
                    "Intake request submitted successfully! "
                    "In the real app this would create a project and route to approvals."
                )
                st.json(form)

    st.session_state["intake_form"] = form


def render_agent_gallery(hub: DemoDataHub, outbox: DemoOutbox) -> None:
    st.header("Agents")
    st.markdown(
        '<p class="ppm-page-desc">Browse, test, and run AI agents from the platform agent registry.</p>',
        unsafe_allow_html=True,
    )
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
    st.header("Analytics What-If")
    st.markdown(
        '<p class="ppm-page-desc">Model budget and scope scenarios to forecast delivery outcomes.</p>',
        unsafe_allow_html=True,
    )
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
    st.header("Artifact Lifecycle")
    st.markdown(
        '<p class="ppm-page-desc">Track artifacts through generation, review, approval, and publication stages.</p>',
        unsafe_allow_html=True,
    )
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
    st.header("Intake Approvals")
    st.markdown(
        '<p class="ppm-page-desc">Review intake requests by approval type: stage gate, template, or publish.</p>',
        unsafe_allow_html=True,
    )
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


# ---------------------------------------------------------------------------
# NEW PAGES — matching React app screens
# ---------------------------------------------------------------------------


def render_enterprise_uplift(hub: DemoDataHub) -> None:
    """Enterprise uplift scenarios matching the React EnterpriseUpliftPage."""
    st.header("Enterprise Uplift")
    st.markdown(
        '<p class="ppm-page-desc">Enterprise-level transformation scenarios and readiness assessments.</p>',
        unsafe_allow_html=True,
    )

    scenarios = [
        {"id": "uplift-01", "name": "Cloud Migration Readiness", "domain": "Infrastructure", "maturity": "Level 3", "target": "Level 4", "status": "In Progress", "score": 72},
        {"id": "uplift-02", "name": "DevOps Capability Uplift", "domain": "Engineering", "maturity": "Level 2", "target": "Level 4", "status": "Planning", "score": 45},
        {"id": "uplift-03", "name": "Data Governance Framework", "domain": "Data & Analytics", "maturity": "Level 1", "target": "Level 3", "status": "Assessment", "score": 28},
        {"id": "uplift-04", "name": "Security Posture Enhancement", "domain": "Security", "maturity": "Level 3", "target": "Level 5", "status": "In Progress", "score": 61},
    ]

    c1, c2, c3 = st.columns(3)
    c1.metric("Active Scenarios", len(scenarios))
    c2.metric("Avg Maturity Score", f"{sum(s['score'] for s in scenarios) // len(scenarios)}%")
    c3.metric("Domains Covered", len({s["domain"] for s in scenarios}))

    st.dataframe(scenarios, hide_index=True, use_container_width=True)

    selected = st.selectbox(
        "Inspect scenario",
        [s["id"] for s in scenarios],
        format_func=lambda sid: next(s["name"] for s in scenarios if s["id"] == sid),
    )
    detail = next(s for s in scenarios if s["id"] == selected)

    st.subheader("Scenario detail")
    d1, d2 = st.columns(2)
    d1.json(detail)
    d2.markdown(
        f"**Assessment Summary**\n"
        f"- **Current Maturity:** {detail['maturity']}\n"
        f"- **Target Maturity:** {detail['target']}\n"
        f"- **Readiness Score:** {detail['score']}%\n"
        f"- **Key Gap:** Process automation and tooling standardisation\n"
        f"- **Recommended Actions:** Define capability roadmap, assign transformation leads"
    )

    render_provenance(hub, "Dashboard")


def render_performance_dashboard(hub: DemoDataHub) -> None:
    """Project performance dashboard matching the React PerformanceDashboardPage."""
    st.header("Performance Dashboard")
    st.markdown(
        '<p class="ppm-page-desc">Detailed project performance metrics including earned value, schedule, and budget analysis.</p>',
        unsafe_allow_html=True,
    )

    project_id = st.session_state.get("selected_project") or "demo-project-01"
    st.markdown(f'<span class="ppm-badge ppm-badge-default">{project_id}</span>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CPI", "1.02", delta="0.03")
    c2.metric("SPI", "0.97", delta="-0.02")
    c3.metric("Budget Used", "62%", delta="3%")
    c4.metric("Milestones Complete", "4/7")

    tab_ev, tab_budget, tab_schedule = st.tabs(["Earned Value", "Budget", "Schedule"])

    with tab_ev:
        ev_data = [
            {"period": "Week 1", "PV": 120, "EV": 118, "AC": 115},
            {"period": "Week 2", "PV": 240, "EV": 235, "AC": 230},
            {"period": "Week 3", "PV": 360, "EV": 350, "AC": 345},
            {"period": "Week 4", "PV": 480, "EV": 465, "AC": 455},
            {"period": "Week 5", "PV": 600, "EV": 582, "AC": 570},
            {"period": "Week 6", "PV": 720, "EV": 698, "AC": 742},
        ]
        st.dataframe(ev_data, hide_index=True, use_container_width=True)
        st.caption("PV = Planned Value (£k) | EV = Earned Value (£k) | AC = Actual Cost (£k)")

    with tab_budget:
        budget_data = [
            {"category": "Personnel", "budget": 650, "actual": 420, "forecast": 640, "variance": "+10k"},
            {"category": "Infrastructure", "budget": 280, "actual": 195, "forecast": 285, "variance": "-5k"},
            {"category": "Licensing", "budget": 120, "actual": 78, "forecast": 118, "variance": "+2k"},
            {"category": "Contingency", "budget": 150, "actual": 49, "forecast": 147, "variance": "+3k"},
        ]
        st.dataframe(budget_data, hide_index=True, use_container_width=True)

    with tab_schedule:
        schedule_data = [
            {"milestone": "Charter sign-off", "baseline": "2026-02-28", "actual": "2026-02-28", "variance": "0d", "status": "Complete"},
            {"milestone": "Design gate exit", "baseline": "2026-03-14", "actual": "2026-03-14", "variance": "0d", "status": "Complete"},
            {"milestone": "Sprint 5 start", "baseline": "2026-03-17", "actual": "2026-03-17", "variance": "0d", "status": "Complete"},
            {"milestone": "Sprint 6 start", "baseline": "2026-03-31", "actual": "2026-04-14", "variance": "+14d", "status": "At Risk"},
            {"milestone": "UAT Phase 2", "baseline": "2026-04-07", "forecast": "2026-04-21", "variance": "+14d", "status": "Upcoming"},
            {"milestone": "Go-live", "baseline": "2026-04-28", "forecast": "2026-05-12", "variance": "+14d", "status": "Upcoming"},
        ]
        st.dataframe(schedule_data, hide_index=True, use_container_width=True)

    render_provenance(hub, "Dashboard")


def render_workflow_monitoring(hub: DemoDataHub) -> None:
    """Workflow monitoring matching the React WorkflowMonitoringPage."""
    st.header("Workflow Monitoring")
    st.markdown(
        '<p class="ppm-page-desc">Monitor active workflow instances, step status, and real-time execution events.</p>',
        unsafe_allow_html=True,
    )

    workflows = [
        {"instance_id": "wf-run-001", "workflow": "Intake > Approval > Provisioning", "status": "running", "current_step": "Approval Gate", "started_at": "2026-02-23T08:12:00Z", "steps_done": 2, "total_steps": 5},
        {"instance_id": "wf-run-002", "workflow": "Agent Orchestration Pipeline", "status": "completed", "current_step": "Done", "started_at": "2026-02-22T14:30:00Z", "steps_done": 4, "total_steps": 4},
        {"instance_id": "wf-run-003", "workflow": "Artifact Review Cycle", "status": "waiting", "current_step": "Reviewer Assignment", "started_at": "2026-02-23T09:45:00Z", "steps_done": 1, "total_steps": 6},
        {"instance_id": "wf-run-004", "workflow": "Stage Gate Assessment", "status": "failed", "current_step": "Compliance Check", "started_at": "2026-02-22T16:00:00Z", "steps_done": 3, "total_steps": 5},
    ]

    c1, c2, c3 = st.columns(3)
    c1.metric("Active Workflows", sum(1 for w in workflows if w["status"] == "running"))
    c2.metric("Completed Today", sum(1 for w in workflows if w["status"] == "completed"))
    c3.metric("Total Instances", len(workflows))

    st.markdown(
        '<span class="ppm-badge ppm-badge-success">Stream: Connected</span>',
        unsafe_allow_html=True,
    )

    st.dataframe(workflows, hide_index=True, use_container_width=True)

    selected = st.selectbox(
        "Inspect workflow",
        [w["instance_id"] for w in workflows],
        format_func=lambda wid: next(
            f"{w['instance_id']} \u2014 {w['workflow']}" for w in workflows if w["instance_id"] == wid
        ),
    )
    detail = next(w for w in workflows if w["instance_id"] == selected)

    st.subheader("Workflow timeline")
    events = [
        {"step": 1, "name": "Trigger received", "status": "completed", "timestamp": detail["started_at"]},
        {"step": 2, "name": "Validation & routing", "status": "completed", "timestamp": "2026-02-23T08:12:30Z"},
        {"step": 3, "name": detail["current_step"], "status": detail["status"], "timestamp": "2026-02-23T08:13:00Z"},
    ]
    st.dataframe(events, hide_index=True, use_container_width=True)
    st.json(detail)

    if st.button("Trigger sample workflow", key="btn-trigger-workflow"):
        st.success("Sample workflow triggered: wf-run-005 (Intake > Approval > Provisioning)")

    render_provenance(hub, "Dashboard")


def render_workflow_designer(hub: DemoDataHub) -> None:
    """Workflow designer matching the React WorkflowDesigner (simplified table view)."""
    st.header("Workflow Designer")
    st.markdown(
        '<p class="ppm-page-desc">Design and configure workflow orchestration rules with visual node editing.</p>',
        unsafe_allow_html=True,
    )

    node_types = ["task", "decision", "approval", "notification", "api", "script"]

    if "wf_designer_nodes" not in st.session_state:
        st.session_state["wf_designer_nodes"] = [
            {"node_id": "node-1", "type": "task", "label": "Receive intake request", "agent": "agent-01", "position": 1},
            {"node_id": "node-2", "type": "decision", "label": "Check duplicates", "agent": "agent-02", "position": 2},
            {"node_id": "node-3", "type": "approval", "label": "Manager approval gate", "agent": None, "position": 3},
            {"node_id": "node-4", "type": "notification", "label": "Notify stakeholders", "agent": "agent-05", "position": 4},
            {"node_id": "node-5", "type": "task", "label": "Provision workspace", "agent": "agent-03", "position": 5},
        ]
    if "wf_designer_edges" not in st.session_state:
        st.session_state["wf_designer_edges"] = [
            {"from": "node-1", "to": "node-2", "condition": "always"},
            {"from": "node-2", "to": "node-3", "condition": "no_duplicate"},
            {"from": "node-2", "to": "node-4", "condition": "duplicate_found"},
            {"from": "node-3", "to": "node-5", "condition": "approved"},
        ]

    tab_nodes, tab_edges, tab_routing = st.tabs(["Nodes", "Connections", "Routing Rules"])

    with tab_nodes:
        st.dataframe(st.session_state["wf_designer_nodes"], hide_index=True, use_container_width=True)
        st.subheader("Add node")
        nc1, nc2, nc3 = st.columns(3)
        new_type = nc1.selectbox("Node type", node_types, key="wfd-node-type")
        new_label = nc2.text_input("Label", key="wfd-node-label")
        new_agent = nc3.text_input("Agent (optional)", key="wfd-node-agent")
        if st.button("Add node", key="btn-add-wf-node"):
            if new_label.strip():
                next_id = f"node-{len(st.session_state['wf_designer_nodes']) + 1}"
                st.session_state["wf_designer_nodes"].append({
                    "node_id": next_id, "type": new_type, "label": new_label.strip(),
                    "agent": new_agent.strip() or None,
                    "position": len(st.session_state["wf_designer_nodes"]) + 1,
                })
                st.success(f"Added node {next_id}")

    with tab_edges:
        st.dataframe(st.session_state["wf_designer_edges"], hide_index=True, use_container_width=True)
        st.subheader("Add connection")
        node_ids = [n["node_id"] for n in st.session_state["wf_designer_nodes"]]
        ec1, ec2, ec3 = st.columns(3)
        from_node = ec1.selectbox("From", node_ids, key="wfd-edge-from")
        to_node = ec2.selectbox("To", node_ids, key="wfd-edge-to")
        condition = ec3.text_input("Condition", value="always", key="wfd-edge-condition")
        if st.button("Add connection", key="btn-add-wf-edge"):
            st.session_state["wf_designer_edges"].append(
                {"from": from_node, "to": to_node, "condition": condition}
            )
            st.success("Connection added")

    with tab_routing:
        routing_rules = [
            {"intent": "intake.submit", "agent": "agent-01", "priority": 1, "dependency": None},
            {"intent": "duplicate.check", "agent": "agent-02", "priority": 2, "dependency": "agent-01"},
            {"intent": "approval.route", "agent": "agent-04", "priority": 3, "dependency": "agent-02"},
            {"intent": "workspace.provision", "agent": "agent-03", "priority": 4, "dependency": "agent-04"},
        ]
        st.dataframe(routing_rules, hide_index=True, use_container_width=True)

    bc1, bc2 = st.columns(2)
    if bc1.button("Save workflow", key="btn-save-workflow", use_container_width=True):
        st.success("Workflow saved (demo \u2014 persisted in session state)")
    if bc2.button("Reset to default", key="btn-reset-workflow", use_container_width=True):
        st.session_state.pop("wf_designer_nodes", None)
        st.session_state.pop("wf_designer_edges", None)
        st.rerun()


def render_prompt_library(hub: DemoDataHub) -> None:
    """Prompt library manager matching the React PromptManager."""
    st.header("Prompt Library")
    st.markdown(
        '<p class="ppm-page-desc">Create, edit, and manage prompt templates used by AI agents across the platform.</p>',
        unsafe_allow_html=True,
    )

    if "prompt_library" not in st.session_state:
        st.session_state["prompt_library"] = [
            {"id": "prompt-001", "label": "Charter Brief Generator", "description": "Generates a project charter brief from intake data", "tags": "charter, intake, document"},
            {"id": "prompt-002", "label": "Risk Assessment Prompt", "description": "Evaluates project risks and produces a risk register", "tags": "risk, assessment, register"},
            {"id": "prompt-003", "label": "Status Report Summary", "description": "Summarises weekly project status from activity data", "tags": "status, report, weekly"},
            {"id": "prompt-004", "label": "Decision Log Entry", "description": "Creates a structured decision log entry with rationale", "tags": "decision, log, governance"},
            {"id": "prompt-005", "label": "Lessons Learned Extractor", "description": "Extracts lessons learned from retrospective notes", "tags": "lessons, retrospective, knowledge"},
        ]

    prompts = st.session_state["prompt_library"]
    st.metric("Total prompts", len(prompts))

    search = st.text_input("Search prompts", key="prompt-search", placeholder="Filter by label, description, or tags...")
    if search.strip():
        token = search.strip().lower()
        visible = [
            p for p in prompts
            if token in p["label"].lower() or token in p["description"].lower() or token in p["tags"].lower()
        ]
    else:
        visible = prompts

    st.dataframe(visible, hide_index=True, use_container_width=True)

    st.subheader("Create / edit prompt")
    pc1, pc2 = st.columns(2)
    edit_label = pc1.text_input("Label", key="pl-label")
    edit_tags = pc2.text_input("Tags (comma-separated)", key="pl-tags")
    edit_desc = st.text_area("Description", key="pl-desc", height=80)

    bc1, bc2 = st.columns(2)
    if bc1.button("Save prompt", key="btn-save-prompt", use_container_width=True):
        if edit_label.strip():
            new_id = f"prompt-{len(prompts) + 1:03d}"
            st.session_state["prompt_library"].append({
                "id": new_id, "label": edit_label.strip(),
                "description": edit_desc.strip(), "tags": edit_tags.strip(),
            })
            st.success(f"Saved prompt {new_id}: {edit_label}")
    if bc2.button("Delete last prompt", key="btn-delete-prompt", use_container_width=True):
        if prompts:
            removed = st.session_state["prompt_library"].pop()
            st.success(f"Deleted prompt {removed['id']}")


def render_methodology_editor(hub: DemoDataHub) -> None:
    """Methodology editor matching the React MethodologyEditor."""
    st.header("Methodology Editor")
    st.markdown(
        '<p class="ppm-page-desc">Create and configure methodology stages, activities, and canvas type assignments.</p>',
        unsafe_allow_html=True,
    )

    canvas_types = [
        "document", "tree", "timeline", "spreadsheet", "dashboard",
        "board", "backlog", "gantt", "grid", "financial",
        "dependency_map", "roadmap", "approval",
    ]

    methodologies = hub.methodologies()
    method_ids = [m.id for m in methodologies]
    selected_method_id = st.selectbox(
        "Methodology",
        method_ids,
        format_func=lambda mid: next((m.name for m in methodologies if m.id == mid), mid),
        key="me-methodology",
    )
    selected_method = find_methodology(methodologies, selected_method_id)

    if selected_method:
        for stage in selected_method.stages:
            with st.expander(f"Stage: {stage.name} ({len(stage.activities)} activities)", expanded=False):
                details_map = hub.methodology_activity_details()
                activity_rows = []
                for activity in stage.activities:
                    d = details_map.get(activity.id, {})
                    activity_rows.append({
                        "activity_id": activity.id,
                        "activity_name": activity.name,
                        "canvas_type": d.get("canvas_type", "document"),
                        "status": d.get("status", "not_started"),
                    })
                st.dataframe(activity_rows, hide_index=True, use_container_width=True)

    st.subheader("Add activity (demo)")
    ac1, ac2, ac3 = st.columns(3)
    new_activity_name = ac1.text_input("Activity name", key="me-activity-name")
    new_canvas_type = ac2.selectbox("Canvas type", canvas_types, key="me-canvas-type")
    new_prereqs = ac3.text_input("Prerequisites (comma-separated)", key="me-prereqs")
    if st.button("Add activity (session only)", key="btn-add-activity"):
        if new_activity_name.strip():
            st.success(
                f"Activity '{new_activity_name}' added with canvas type '{new_canvas_type}' (demo \u2014 session only)"
            )
            st.json({"activity_name": new_activity_name, "canvas_type": new_canvas_type, "prerequisites": new_prereqs})


def render_role_manager(hub: DemoDataHub) -> None:
    """Role manager matching the React RoleManager."""
    st.header("Role Management")
    st.markdown(
        '<p class="ppm-page-desc">Manage platform roles, permissions, and user-role assignments.</p>',
        unsafe_allow_html=True,
    )

    if "demo_roles" not in st.session_state:
        st.session_state["demo_roles"] = [
            {"role_id": "admin", "name": "Administrator", "description": "Full platform access", "permissions": "audit.view, roles.manage, config.manage, llm.manage, intake.approve, methodology.edit"},
            {"role_id": "pm", "name": "Project Manager", "description": "Project workspace and intake management", "permissions": "intake.approve, methodology.edit, config.manage"},
            {"role_id": "reviewer", "name": "Reviewer", "description": "Approval and review permissions", "permissions": "intake.approve, audit.view"},
            {"role_id": "viewer", "name": "Viewer", "description": "Read-only access", "permissions": "audit.view"},
        ]
    if "demo_role_assignments" not in st.session_state:
        st.session_state["demo_role_assignments"] = [
            {"user_id": "sophie.lang", "roles": "admin, pm", "assigned_at": "2026-02-01T09:00:00Z"},
            {"user_id": "marcus.reed", "roles": "pm, reviewer", "assigned_at": "2026-02-05T10:30:00Z"},
            {"user_id": "priya.shah", "roles": "reviewer", "assigned_at": "2026-02-10T14:00:00Z"},
            {"user_id": "demo.user", "roles": "admin", "assigned_at": "2026-02-15T08:00:00Z"},
        ]

    tab_roles, tab_assignments = st.tabs(["Roles", "Assignments"])

    with tab_roles:
        st.dataframe(st.session_state["demo_roles"], hide_index=True, use_container_width=True)
        st.subheader("Create role")
        rc1, rc2 = st.columns(2)
        new_role_id = rc1.text_input("Role ID", key="rm-role-id")
        new_role_name = rc2.text_input("Role name", key="rm-role-name")
        new_role_desc = st.text_input("Description", key="rm-role-desc")

        st.markdown("**Permissions**")
        perms = ["audit.view", "roles.manage", "config.manage", "llm.manage", "intake.approve", "methodology.edit"]
        selected_perms: list[str] = []
        perm_cols = st.columns(3)
        for i, perm in enumerate(perms):
            if perm_cols[i % 3].checkbox(perm, key=f"rm-perm-{perm}"):
                selected_perms.append(perm)

        if st.button("Create role", key="btn-create-role"):
            if new_role_id.strip() and new_role_name.strip():
                st.session_state["demo_roles"].append({
                    "role_id": new_role_id.strip(), "name": new_role_name.strip(),
                    "description": new_role_desc.strip(), "permissions": ", ".join(selected_perms),
                })
                st.success(f"Created role: {new_role_name}")

    with tab_assignments:
        st.dataframe(st.session_state["demo_role_assignments"], hide_index=True, use_container_width=True)
        st.subheader("Assign role")
        ac1, ac2 = st.columns(2)
        assign_user = ac1.text_input("User ID", key="rm-assign-user")
        assign_roles = ac2.text_input("Roles (comma-separated)", key="rm-assign-roles")
        if st.button("Assign", key="btn-assign-role"):
            if assign_user.strip():
                st.session_state["demo_role_assignments"].append({
                    "user_id": assign_user.strip(), "roles": assign_roles.strip(),
                    "assigned_at": datetime.now(tz=UTC).isoformat(),
                })
                st.success(f"Assigned roles to {assign_user}")


def render_merge_review(hub: DemoDataHub) -> None:
    """Merge review for duplicate intake requests matching the React MergeReviewPage."""
    st.header("Merge Review")
    st.markdown(
        '<p class="ppm-page-desc">Review and resolve duplicate intake requests identified by the deduplication agent.</p>',
        unsafe_allow_html=True,
    )

    duplicates = [
        {
            "pair_id": "dup-001", "request_a": "intake-001", "request_b": "intake-004",
            "similarity": 0.87, "field_overlap": "sponsor_name, business_summary",
            "status": "pending", "recommended_action": "merge",
        },
        {
            "pair_id": "dup-002", "request_a": "intake-002", "request_b": "intake-005",
            "similarity": 0.72, "field_overlap": "department, expected_benefits",
            "status": "pending", "recommended_action": "review",
        },
    ]

    st.metric("Pending duplicates", len([d for d in duplicates if d["status"] == "pending"]))
    st.dataframe(duplicates, hide_index=True, use_container_width=True)

    selected = st.selectbox("Select pair", [d["pair_id"] for d in duplicates])
    detail = next(d for d in duplicates if d["pair_id"] == selected)

    st.subheader("Comparison")
    cmp1, cmp2 = st.columns(2)
    cmp1.markdown(f"**Request A:** {detail['request_a']}")
    cmp1.json({
        "request_id": detail["request_a"], "title": "Phoenix Modernization intake",
        "sponsor": "Sophie Lang", "department": "Digital",
    })
    cmp2.markdown(f"**Request B:** {detail['request_b']}")
    cmp2.json({
        "request_id": detail["request_b"], "title": "Phoenix Modernisation Phase 2",
        "sponsor": "Sophie Lang", "department": "Digital",
    })

    st.markdown(
        f"**Similarity:** {detail['similarity']:.0%} | **Overlapping fields:** {detail['field_overlap']}"
    )

    mc1, mc2, mc3 = st.columns(3)
    if mc1.button("Merge (keep A)", key="btn-merge-a", use_container_width=True):
        st.success(f"Merged: kept {detail['request_a']}, archived {detail['request_b']}")
    if mc2.button("Merge (keep B)", key="btn-merge-b", use_container_width=True):
        st.success(f"Merged: kept {detail['request_b']}, archived {detail['request_a']}")
    if mc3.button("Not duplicate", key="btn-not-dup", use_container_width=True):
        st.success("Marked as not duplicate")


def render_document_search(hub: DemoDataHub) -> None:
    """Document search matching the React DocumentSearchPage."""
    st.header("Documents")
    st.markdown(
        '<p class="ppm-page-desc">Search and browse project documents with version history.</p>',
        unsafe_allow_html=True,
    )

    documents = [
        {"doc_id": "doc-001", "title": "Project Charter \u2014 Phoenix Modernization", "type": "charter", "project": "demo-project-01", "version": 3, "updated_at": "2026-02-20T14:30:00Z", "author": "S. Lang"},
        {"doc_id": "doc-002", "title": "Work Breakdown Structure v2", "type": "wbs", "project": "demo-project-01", "version": 2, "updated_at": "2026-02-18T09:15:00Z", "author": "M. Reed"},
        {"doc_id": "doc-003", "title": "Risk Register Q1 2026", "type": "risk_register", "project": "demo-project-01", "version": 5, "updated_at": "2026-02-22T16:45:00Z", "author": "H. Cole"},
        {"doc_id": "doc-004", "title": "Budget Tracker FY26", "type": "budget", "project": "demo-project-02", "version": 1, "updated_at": "2026-02-15T11:00:00Z", "author": "P. Shah"},
        {"doc_id": "doc-005", "title": "Sprint 5 Retrospective Notes", "type": "retrospective", "project": "demo-project-01", "version": 1, "updated_at": "2026-02-21T17:30:00Z", "author": "E. Brooks"},
        {"doc_id": "doc-006", "title": "Architecture Decision Record \u2014 Auth", "type": "adr", "project": "demo-project-01", "version": 2, "updated_at": "2026-02-19T10:00:00Z", "author": "K. Patel"},
    ]

    sc1, sc2 = st.columns([3, 1])
    search = sc1.text_input("Search documents", key="doc-search", placeholder="Search by title or content...")
    project_filter = sc2.selectbox(
        "Project", ["All"] + sorted({d["project"] for d in documents}), key="doc-project-filter",
    )

    visible = documents
    if search.strip():
        token = search.strip().lower()
        visible = [d for d in visible if token in d["title"].lower() or token in d["type"].lower()]
    if project_filter != "All":
        visible = [d for d in visible if d["project"] == project_filter]

    st.metric("Documents found", len(visible))
    st.dataframe(visible, hide_index=True, use_container_width=True)

    if visible:
        selected_doc = st.selectbox(
            "View document",
            [d["doc_id"] for d in visible],
            format_func=lambda did: next(d["title"] for d in visible if d["doc_id"] == did),
        )
        doc = next(d for d in visible if d["doc_id"] == selected_doc)

        st.subheader("Document detail")
        d1, d2 = st.columns(2)
        d1.json(doc)
        d2.markdown(
            f"**Version history**\n\n"
            f"| Version | Author | Date |\n|---------|--------|------|\n"
            f"| v{doc['version']} (current) | {doc['author']} | {doc['updated_at'][:10]} |\n"
            f"| v{max(1, doc['version'] - 1)} | {doc['author']} | 2026-02-14 |\n"
            f"| v1 | Platform Admin | 2026-02-01 |"
        )

    if st.button("Refresh documents", key="btn-refresh-docs"):
        st.success("Documents refreshed from project workspace")


def render_lessons_learned(hub: DemoDataHub) -> None:
    """Lessons learned matching the React LessonsLearnedPage."""
    st.header("Lessons Learned")
    st.markdown(
        '<p class="ppm-page-desc">Capture, search, and share lessons learned across projects and methodologies.</p>',
        unsafe_allow_html=True,
    )

    if "demo_lessons" not in st.session_state:
        st.session_state["demo_lessons"] = [
            {"id": "lesson-001", "title": "Early stakeholder alignment reduces rework", "description": "Engaging stakeholders in the Discover stage reduced design rework by 40%", "tags": "stakeholder, discover, rework", "topic": "Governance", "stage": "Discover"},
            {"id": "lesson-002", "title": "Automated gate checks improve throughput", "description": "Implementing automated stage gate compliance checks cut approval time from 5 days to 1 day", "tags": "automation, gate, approval", "topic": "Process", "stage": "Deliver"},
            {"id": "lesson-003", "title": "Risk register weekly review cadence", "description": "Weekly risk register reviews caught 3 critical issues before they impacted the schedule", "tags": "risk, review, weekly", "topic": "Risk Management", "stage": "Deliver"},
            {"id": "lesson-004", "title": "Budget contingency allocation guidance", "description": "Allocating 12-15% contingency proved optimal for projects in the 500k-1.5M range", "tags": "budget, contingency, financial", "topic": "Financial", "stage": "Design"},
        ]

    lessons = st.session_state["demo_lessons"]

    sc1, sc2 = st.columns([3, 1])
    search = sc1.text_input("Search lessons", key="ll-search", placeholder="Search by title, description, or tags...")
    topic_filter = sc2.selectbox(
        "Topic", ["All"] + sorted({l_item["topic"] for l_item in lessons}), key="ll-topic-filter",
    )

    visible = lessons
    if search.strip():
        token = search.strip().lower()
        visible = [
            l_item for l_item in visible
            if token in l_item["title"].lower() or token in l_item["description"].lower() or token in l_item["tags"].lower()
        ]
    if topic_filter != "All":
        visible = [l_item for l_item in visible if l_item["topic"] == topic_filter]

    st.dataframe(visible, hide_index=True, use_container_width=True)

    st.subheader("Create lesson")
    lc1, lc2 = st.columns(2)
    new_title = lc1.text_input("Title", key="ll-title")
    new_topic = lc2.selectbox(
        "Topic",
        ["Governance", "Process", "Risk Management", "Financial", "Technical", "People"],
        key="ll-topic",
    )
    new_desc = st.text_area("Description", key="ll-desc", height=80)
    new_tags = st.text_input("Tags (comma-separated)", key="ll-tags")

    bc1, bc2 = st.columns(2)
    if bc1.button("Save lesson", key="btn-save-lesson", use_container_width=True):
        if new_title.strip():
            new_id = f"lesson-{len(lessons) + 1:03d}"
            st.session_state["demo_lessons"].append({
                "id": new_id, "title": new_title.strip(), "description": new_desc.strip(),
                "tags": new_tags.strip(), "topic": new_topic, "stage": "General",
            })
            st.success(f"Saved lesson: {new_title}")
    if bc2.button("Delete last lesson", key="btn-delete-lesson", use_container_width=True):
        if lessons:
            removed = st.session_state["demo_lessons"].pop()
            st.success(f"Deleted: {removed['title']}")

    st.subheader("AI Recommendations")
    st.info("Based on your current project stage and activity, the following lessons may be relevant:")
    stage = st.session_state.get("selected_stage_name", "Discover")
    relevant = [l_item for l_item in lessons if l_item.get("stage", "").lower() == stage.lower()]
    if relevant:
        for l_item in relevant[:3]:
            st.markdown(f"- **{l_item['title']}** \u2014 {l_item['description']}")
    else:
        st.markdown("No stage-specific recommendations available. Try browsing all lessons above.")


def render_global_search(hub: DemoDataHub) -> None:
    """Global search matching the React GlobalSearchPage."""
    st.header("Search")
    st.markdown(
        '<p class="ppm-page-desc">Search across documents, projects, knowledge base, approvals, and workflows.</p>',
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "Search everything", key="global-search-query",
        placeholder="Search documents, projects, approvals...",
    )

    sc1, sc2 = st.columns(2)
    type_filter = sc1.selectbox(
        "Type", ["All", "Documents", "Projects", "Approvals", "Workflows", "Knowledge"],
        key="gs-type-filter",
    )
    sc2.selectbox(
        "Date range", ["All time", "Last 7 days", "Last 30 days", "Last 90 days"],
        key="gs-date-filter",
    )

    all_results = [
        {"type": "Documents", "title": "Project Charter \u2014 Phoenix Modernization", "match": "charter modernization phoenix", "relevance": 0.95, "updated": "2026-02-20"},
        {"type": "Projects", "title": "Phoenix Modernization", "match": "phoenix modernization project demo-project-01", "relevance": 0.92, "updated": "2026-02-22"},
        {"type": "Approvals", "title": "Stage gate approval \u2014 Design phase", "match": "stage gate design approval review", "relevance": 0.88, "updated": "2026-02-21"},
        {"type": "Workflows", "title": "Intake Approval Pipeline", "match": "intake approval pipeline workflow", "relevance": 0.85, "updated": "2026-02-23"},
        {"type": "Knowledge", "title": "Early stakeholder alignment reduces rework", "match": "stakeholder alignment rework lesson", "relevance": 0.80, "updated": "2026-02-19"},
        {"type": "Documents", "title": "Risk Register Q1 2026", "match": "risk register 2026 quarterly", "relevance": 0.78, "updated": "2026-02-22"},
        {"type": "Projects", "title": "Atlas Migration", "match": "atlas migration data platform", "relevance": 0.75, "updated": "2026-02-18"},
        {"type": "Approvals", "title": "Budget supplement 25k", "match": "budget supplement approval financial", "relevance": 0.72, "updated": "2026-02-22"},
    ]

    results = all_results
    if query.strip():
        token = query.strip().lower()
        results = [r for r in results if token in r["match"] or token in r["title"].lower()]
    if type_filter != "All":
        results = [r for r in results if r["type"] == type_filter]

    st.metric("Results", len(results))

    if results:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for r in results:
            grouped.setdefault(r["type"], []).append(r)
        for type_name, items in grouped.items():
            st.subheader(f"{type_name} ({len(items)})")
            st.dataframe(items, hide_index=True, use_container_width=True)
    elif query.strip():
        st.info("No results found. Try broadening your search.")


def render_connector_marketplace(hub: DemoDataHub) -> None:
    """Connector marketplace matching the React ConnectorMarketplacePage."""
    st.header("Connector Marketplace")
    st.markdown(
        '<p class="ppm-page-desc">Browse and install available connectors to integrate with external tools and services.</p>',
        unsafe_allow_html=True,
    )

    marketplace = [
        {"connector_id": "jira-cloud", "name": "Jira Cloud", "category": "Project Management", "status": "available", "rating": 4.8, "installs": 1250, "description": "Sync issues, sprints, and boards with Jira Cloud"},
        {"connector_id": "azure-devops", "name": "Azure DevOps", "category": "DevOps", "status": "available", "rating": 4.6, "installs": 980, "description": "Work items, pipelines, and repos integration"},
        {"connector_id": "servicenow", "name": "ServiceNow", "category": "ITSM", "status": "available", "rating": 4.5, "installs": 720, "description": "Incident, change, and problem management sync"},
        {"connector_id": "sharepoint", "name": "SharePoint Online", "category": "Document Management", "status": "installed", "rating": 4.7, "installs": 1100, "description": "Document libraries and site integration"},
        {"connector_id": "power-bi", "name": "Power BI", "category": "Analytics", "status": "available", "rating": 4.4, "installs": 650, "description": "Dashboard and report embedding"},
        {"connector_id": "slack", "name": "Slack", "category": "Communication", "status": "installed", "rating": 4.9, "installs": 2100, "description": "Channel notifications and command integration"},
        {"connector_id": "ms-teams", "name": "Microsoft Teams", "category": "Communication", "status": "available", "rating": 4.5, "installs": 1800, "description": "Teams channels, meetings, and bot integration"},
        {"connector_id": "sap", "name": "SAP S/4HANA", "category": "ERP", "status": "available", "rating": 4.2, "installs": 340, "description": "Financial and procurement data integration"},
    ]

    sc1, sc2 = st.columns([3, 1])
    search = sc1.text_input("Search marketplace", key="mp-search", placeholder="Search connectors...")
    category_filter = sc2.selectbox(
        "Category", ["All"] + sorted({c["category"] for c in marketplace}), key="mp-category",
    )

    visible = marketplace
    if search.strip():
        token = search.strip().lower()
        visible = [c for c in visible if token in c["name"].lower() or token in c["description"].lower()]
    if category_filter != "All":
        visible = [c for c in visible if c["category"] == category_filter]

    c1, c2, c3 = st.columns(3)
    c1.metric("Available", len([c for c in marketplace if c["status"] == "available"]))
    c2.metric("Installed", len([c for c in marketplace if c["status"] == "installed"]))
    c3.metric("Categories", len({c["category"] for c in marketplace}))

    st.dataframe(visible, hide_index=True, use_container_width=True)

    if visible:
        selected_conn = st.selectbox(
            "Connector detail",
            [c["connector_id"] for c in visible],
            format_func=lambda cid: next(c["name"] for c in visible if c["connector_id"] == cid),
        )
        detail = next(c for c in visible if c["connector_id"] == selected_conn)
        st.json(detail)

        if detail["status"] == "available":
            if st.button(f"Install {detail['name']}", key="btn-install-connector"):
                st.success(f"Installed {detail['name']} (demo \u2014 session only)")
        else:
            st.info(f"{detail['name']} is already installed")


def render_project_config(hub: DemoDataHub) -> None:
    """Project configuration matching the React ProjectConfigPage."""
    st.header("Project Configuration")
    st.markdown(
        '<p class="ppm-page-desc">Configure project-specific agent and connector settings.</p>',
        unsafe_allow_html=True,
    )

    project_id = st.session_state.get("selected_project") or "demo-project-01"
    st.markdown(f'<span class="ppm-badge ppm-badge-default">{project_id}</span>', unsafe_allow_html=True)

    tab_agents, tab_connectors = st.tabs(["Agents", "Connectors"])

    with tab_agents:
        agent_catalog = hub.normalized_agent_catalog()
        agent_config = []
        for agent in agent_catalog[:10]:
            agent_config.append({
                "agent_id": agent["agent_id"],
                "capability": agent["capability"],
                "enabled": True,
                "maturity": "Production" if int(agent["agent_id"].split("-")[1]) <= 10 else "Beta",
                "parameters": "timeout=120s, retries=3",
            })
        st.dataframe(agent_config, hide_index=True, use_container_width=True)

        selected_agent = st.selectbox("Configure agent", [a["agent_id"] for a in agent_config], key="pc-agent")
        ac1, ac2, ac3 = st.columns(3)
        ac1.text_input("Timeout (s)", value="120", key="pc-timeout")
        ac2.text_input("Retries", value="3", key="pc-retries")
        ac3.checkbox("Enabled", value=True, key="pc-agent-enabled")

        if st.button("Save agent config", key="btn-save-agent-config"):
            st.success(f"Saved config for {selected_agent} (demo \u2014 session only)")

    with tab_connectors:
        connectors = hub.normalized_connectors()
        conn_config = []
        for conn in connectors:
            conn_config.append({
                "connector_id": conn["connector_id"],
                "name": conn["name"],
                "sync_direction": "bidirectional",
                "sync_frequency": "hourly",
                "enabled": True,
            })
        st.dataframe(conn_config, hide_index=True, use_container_width=True)

        if connectors:
            selected_conn_id = st.selectbox(
                "Configure connector", [c["connector_id"] for c in connectors], key="pc-connector",
            )
            cc1, cc2 = st.columns(2)
            cc1.selectbox("Sync direction", ["inbound", "outbound", "bidirectional"], index=2, key="pc-sync-dir")
            cc2.selectbox("Sync frequency", ["realtime", "hourly", "daily", "weekly", "manual"], index=1, key="pc-sync-freq")

            if st.button("Save connector config", key="btn-save-conn-config"):
                st.success(f"Saved config for {selected_conn_id} (demo \u2014 session only)")
            if st.button("Test connector", key="btn-test-connector"):
                st.success(f"Connector {selected_conn_id} test passed (demo)")


# ---------------------------------------------------------------------------
# CANVAS PREVIEW — renders a representative mock for each of 13 canvas types
# ---------------------------------------------------------------------------


def render_canvas_preview(canvas_type: str, activity_name: str) -> None:
    """Render a mock canvas matching the React CanvasWorkspace for the given canvas_type."""
    activity_slug = slugify(activity_name)

    # Toolbar
    toolbar_html = (
        '<div class="ppm-canvas-toolbar">'
        f'<span class="ppm-canvas-toolbar-btn ppm-canvas-toolbar-primary">{friendly_label(canvas_type)}</span>'
        '<span class="ppm-canvas-toolbar-btn">Save draft</span>'
        '<span class="ppm-canvas-toolbar-btn">Publish</span>'
        '<span class="ppm-canvas-toolbar-btn">Export</span>'
        '</div>'
    )

    st.markdown(f'<div class="ppm-canvas-host">{toolbar_html}<div class="ppm-canvas-body">', unsafe_allow_html=True)

    if canvas_type == "document":
        st.markdown(f"### {friendly_label(activity_name)}")
        st.text_area(
            "Document content",
            value=f"# {friendly_label(activity_name)}\n\nDocument canvas for the {activity_name} activity.\n\n"
            "## Section 1\nContent placeholder for section one.\n\n"
            "## Section 2\nContent placeholder for section two.\n\n"
            "---\n*Draft \u2014 AI-generated content pending review.*",
            height=200, key=f"canvas-doc-{activity_slug}",
        )

    elif canvas_type == "tree":
        tree_html = (
            f'<div class="ppm-tree-root">{friendly_label(activity_name)}</div>'
            '<div class="ppm-tree-node">1. Requirements gathering</div>'
            '<div class="ppm-tree-node" style="padding-left:40px;">1.1 Stakeholder interviews</div>'
            '<div class="ppm-tree-node" style="padding-left:40px;">1.2 Document review</div>'
            '<div class="ppm-tree-node">2. Analysis</div>'
            '<div class="ppm-tree-node" style="padding-left:40px;">2.1 Gap analysis</div>'
            '<div class="ppm-tree-node" style="padding-left:40px;">2.2 Impact assessment</div>'
            '<div class="ppm-tree-node">3. Deliverables</div>'
            '<div class="ppm-tree-node" style="padding-left:40px;">3.1 Summary report</div>'
            '<div class="ppm-tree-node" style="padding-left:40px;">3.2 Recommendation deck</div>'
        )
        st.markdown(tree_html, unsafe_allow_html=True)

    elif canvas_type == "timeline":
        milestones = [
            {"milestone": "Kickoff", "date": "2026-03-01", "owner": "PM", "status": "Complete"},
            {"milestone": "Requirements complete", "date": "2026-03-15", "owner": "BA", "status": "Complete"},
            {"milestone": "Design review", "date": "2026-03-28", "owner": "Architect", "status": "In Progress"},
            {"milestone": "Implementation start", "date": "2026-04-05", "owner": "Dev Lead", "status": "Upcoming"},
            {"milestone": "UAT", "date": "2026-04-20", "owner": "QA Lead", "status": "Upcoming"},
            {"milestone": "Go-live", "date": "2026-05-01", "owner": "PM", "status": "Upcoming"},
        ]
        st.dataframe(milestones, hide_index=True, use_container_width=True)

    elif canvas_type == "spreadsheet":
        rows = [
            {"ID": "REQ-001", "Requirement": "User authentication", "Priority": "High", "Status": "Approved", "Owner": "Dev Team"},
            {"ID": "REQ-002", "Requirement": "Data encryption at rest", "Priority": "High", "Status": "In Review", "Owner": "Security"},
            {"ID": "REQ-003", "Requirement": "Audit logging", "Priority": "Medium", "Status": "Approved", "Owner": "Platform"},
            {"ID": "REQ-004", "Requirement": "API rate limiting", "Priority": "Medium", "Status": "Draft", "Owner": "Dev Team"},
            {"ID": "REQ-005", "Requirement": "Dashboard export", "Priority": "Low", "Status": "Draft", "Owner": "Frontend"},
        ]
        st.dataframe(rows, hide_index=True, use_container_width=True)

    elif canvas_type == "dashboard":
        dc1, dc2, dc3, dc4 = st.columns(4)
        dc1.metric("Completion", "68%", delta="5%")
        dc2.metric("Budget Health", "92%", delta="-2%")
        dc3.metric("Open Risks", "3", delta="-1")
        dc4.metric("Pending Actions", "7")

    elif canvas_type == "board":
        bc1, bc2, bc3, bc4 = st.columns(4)
        with bc1:
            st.markdown('<div class="ppm-board-col"><div class="ppm-board-col-title">Backlog</div>'
                        '<div class="ppm-board-card">Define API schema</div>'
                        '<div class="ppm-board-card">Security review</div></div>', unsafe_allow_html=True)
        with bc2:
            st.markdown('<div class="ppm-board-col"><div class="ppm-board-col-title">In Progress</div>'
                        '<div class="ppm-board-card">Auth module</div>'
                        '<div class="ppm-board-card">Data migration</div></div>', unsafe_allow_html=True)
        with bc3:
            st.markdown('<div class="ppm-board-col"><div class="ppm-board-col-title">Review</div>'
                        '<div class="ppm-board-card">Logging setup</div></div>', unsafe_allow_html=True)
        with bc4:
            st.markdown('<div class="ppm-board-col"><div class="ppm-board-col-title">Done</div>'
                        '<div class="ppm-board-card">Env provisioning</div>'
                        '<div class="ppm-board-card">CI pipeline</div></div>', unsafe_allow_html=True)

    elif canvas_type == "backlog":
        backlog = [
            {"rank": 1, "story": "Implement SSO login flow", "points": 8, "sprint": "Sprint 6", "priority": "High"},
            {"rank": 2, "story": "Add role-based access control", "points": 5, "sprint": "Sprint 6", "priority": "High"},
            {"rank": 3, "story": "Build audit trail API", "points": 5, "sprint": "Sprint 7", "priority": "Medium"},
            {"rank": 4, "story": "Create dashboard widgets", "points": 3, "sprint": "Sprint 7", "priority": "Medium"},
            {"rank": 5, "story": "Export reports to PDF", "points": 2, "sprint": "Unassigned", "priority": "Low"},
        ]
        st.dataframe(backlog, hide_index=True, use_container_width=True)

    elif canvas_type == "gantt":
        gantt_data = [
            {"task": "Requirements", "start": "W1", "end": "W2", "duration": "2w", "dependency": "-", "progress": "100%"},
            {"task": "Architecture", "start": "W2", "end": "W3", "duration": "2w", "dependency": "Requirements", "progress": "100%"},
            {"task": "Sprint 5", "start": "W3", "end": "W5", "duration": "2w", "dependency": "Architecture", "progress": "80%"},
            {"task": "Sprint 6", "start": "W5", "end": "W7", "duration": "2w", "dependency": "Sprint 5", "progress": "30%"},
            {"task": "UAT", "start": "W7", "end": "W9", "duration": "2w", "dependency": "Sprint 6", "progress": "0%"},
            {"task": "Go-live", "start": "W9", "end": "W10", "duration": "1w", "dependency": "UAT", "progress": "0%"},
        ]
        st.dataframe(gantt_data, hide_index=True, use_container_width=True)

    elif canvas_type == "grid":
        grid_data = [
            {"entity": "Project Alpha", "status": "Active", "health": "Green", "budget": "92%", "schedule": "On Track"},
            {"entity": "Project Beta", "status": "Active", "health": "Amber", "budget": "78%", "schedule": "At Risk"},
            {"entity": "Project Gamma", "status": "Planning", "health": "Green", "budget": "100%", "schedule": "On Track"},
            {"entity": "Project Delta", "status": "Closing", "health": "Green", "budget": "95%", "schedule": "Complete"},
        ]
        st.dataframe(grid_data, hide_index=True, use_container_width=True)

    elif canvas_type == "financial":
        fin_data = [
            {"line_item": "Personnel", "budget": 650, "actual_ytd": 420, "committed": 580, "forecast": 640, "variance": 10},
            {"line_item": "Infrastructure", "budget": 280, "actual_ytd": 195, "committed": 240, "forecast": 285, "variance": -5},
            {"line_item": "Licensing", "budget": 120, "actual_ytd": 78, "committed": 100, "forecast": 118, "variance": 2},
            {"line_item": "Contingency", "budget": 150, "actual_ytd": 49, "committed": 49, "forecast": 147, "variance": 3},
            {"line_item": "TOTAL", "budget": 1200, "actual_ytd": 742, "committed": 969, "forecast": 1190, "variance": 10},
        ]
        st.dataframe(fin_data, hide_index=True, use_container_width=True)
        st.caption("All figures in \u00a3k")

    elif canvas_type == "dependency_map":
        deps = [
            {"from_node": "Auth Module", "to_node": "API Gateway", "type": "blocks", "status": "resolved"},
            {"from_node": "API Gateway", "to_node": "Frontend App", "type": "blocks", "status": "active"},
            {"from_node": "Data Migration", "to_node": "Reporting Module", "type": "blocks", "status": "active"},
            {"from_node": "Vendor Integration", "to_node": "Auth Module", "type": "depends_on", "status": "at_risk"},
            {"from_node": "CI Pipeline", "to_node": "All Modules", "type": "supports", "status": "resolved"},
        ]
        st.dataframe(deps, hide_index=True, use_container_width=True)

    elif canvas_type == "roadmap":
        lanes_html = (
            '<div class="ppm-lane"><div class="ppm-lane-title">Q1 2026</div>'
            '<div class="ppm-board-card">Foundation &amp; Architecture</div>'
            '<div class="ppm-board-card">Security Framework</div></div>'
            '<div class="ppm-lane"><div class="ppm-lane-title">Q2 2026</div>'
            '<div class="ppm-board-card">Core Feature Delivery</div>'
            '<div class="ppm-board-card">Integration Layer</div></div>'
            '<div class="ppm-lane"><div class="ppm-lane-title">Q3 2026</div>'
            '<div class="ppm-board-card">Scale &amp; Optimisation</div>'
            '<div class="ppm-board-card">Advanced Analytics</div></div>'
            '<div class="ppm-lane"><div class="ppm-lane-title">Q4 2026</div>'
            '<div class="ppm-board-card">Enterprise Rollout</div>'
            '<div class="ppm-board-card">Continuous Improvement</div></div>'
        )
        st.markdown(lanes_html, unsafe_allow_html=True)

    elif canvas_type == "approval":
        steps_html = (
            '<div class="ppm-approval-step"><span class="ppm-badge ppm-badge-success">Approved</span> Author submits draft</div>'
            '<div class="ppm-approval-step"><span class="ppm-badge ppm-badge-success">Approved</span> Peer review complete</div>'
            '<div class="ppm-approval-step"><span class="ppm-badge ppm-badge-warning">Pending</span> Manager approval</div>'
            '<div class="ppm-approval-step"><span class="ppm-badge ppm-badge-default">Waiting</span> Quality gate</div>'
            '<div class="ppm-approval-step"><span class="ppm-badge ppm-badge-default">Waiting</span> Publish to workspace</div>'
        )
        st.markdown(steps_html, unsafe_allow_html=True)

    else:
        st.info(f"Canvas type '{canvas_type}' preview not available.")

    st.markdown('</div></div>', unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="PPM Platform",
        page_icon="\U0001f4cb",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_demo_styles()

    hub = get_data_hub()
    init_state(hub)
    outbox = DemoOutbox(OUTBOX_PATH)
    engine = DemoRunEngine(hub.normalized_demo_run(), outbox)

    # ===== SIDEBAR — structured like the React LeftPanel =====
    st.sidebar.markdown(
        '<div class="sidebar-header"><span>Navigation</span></div>',
        unsafe_allow_html=True,
    )

    # Build ordered navigation with section separators — matches React LeftPanel
    nav_pages_navigate = ["Home", "Demo Run", "Enterprise Uplift", "Collections"]
    nav_pages_work = ["New Intake", "Intake", "Approvals", "Workspace", "Performance"]
    nav_pages_insights = ["Dashboard", "Analytics What-If", "Documents", "Lessons Learned", "Search"]
    nav_pages_admin = [
        "Agents",
        "Connectors",
        "Marketplace",
        "Workflow Monitor",
        "Workflow Designer",
        "Prompt Library",
        "Methodology Editor",
        "Role Manager",
        "Project Config",
        "Artifact Lifecycle",
        "Audit",
    ]
    if st.session_state["feature_flags"].get("duplicate_resolution"):
        nav_pages_admin.append("Merge Review")
    if st.session_state["feature_flags"].get("agent_async_notifications"):
        nav_pages_admin.append("Notifications")
    if st.session_state["feature_flags"].get("agent_run_ui"):
        nav_pages_admin.append("Agent Runs")

    nav_pages = nav_pages_navigate + nav_pages_work + nav_pages_insights + nav_pages_admin

    # Render section headers above the nav radio using markdown
    _nav_sections = [
        ("NAVIGATE", nav_pages_navigate),
        ("WORK", nav_pages_work),
        ("INSIGHTS", nav_pages_insights),
        ("ADMIN", nav_pages_admin),
    ]

    # Compute CSS nth-child indices for section dividers
    # We'll add top-border styling to the first item of each section
    _section_starts: list[int] = []
    _offset = 0
    for _sect_name, _sect_pages in _nav_sections:
        if _offset > 0:
            _section_starts.append(_offset)
        _offset += len(_sect_pages)

    # Inject CSS for section dividers within the radio group
    _section_css = ""
    for idx in _section_starts:
        # CSS nth-child is 1-indexed
        _section_css += f"""
            [data-testid="stSidebar"] [role="radiogroup"] > label:nth-child({idx + 1}) {{
                margin-top: 12px !important;
                padding-top: 12px !important;
                border-top: 1px solid #EEEFF1 !important;
            }}
        """
    if _section_css:
        st.sidebar.markdown(f"<style>{_section_css}</style>", unsafe_allow_html=True)

    if st.session_state.get("active_page") in nav_pages:
        st.session_state["selected_page"] = st.session_state["active_page"]

    # Ensure selected page is valid
    if st.session_state.get("selected_page") not in nav_pages:
        st.session_state["selected_page"] = "Home"

    st.session_state["selected_page"] = st.sidebar.radio(
        "Pages",
        nav_pages,
        index=nav_pages.index(st.session_state["selected_page"]),
        label_visibility="collapsed",
    )
    st.session_state["active_page"] = st.session_state["selected_page"]

    # --- Scenario selectors (in collapsible expander) ---
    with st.sidebar.expander("Scenario & Flags", expanded=False):
        render_scenario_selectors_sidebar(hub)
        st.markdown("---")
        render_feature_flags_panel()

    # ===== MAIN CONTENT AREA =====
    page = st.session_state["selected_page"]

    # Header bar
    render_html_header(page)

    # Layout: main content (70%) + assistant panel (30%) — matches React proportions
    left, right = st.columns([7, 3], gap="medium")

    with left:
        if page == "Home":
            render_home(hub)
        elif page == "Collections":
            render_collections(hub)
        elif page == "Workspace":
            render_workspace(hub)
        elif page == "New Intake":
            render_new_intake(hub)
        elif page == "Intake":
            render_intake(hub)
        elif page == "Approvals":
            render_approvals_advanced(hub)
        elif page == "Artifact Lifecycle":
            render_artifact_lifecycle(hub)
        elif page == "Agents":
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
        elif page == "Enterprise Uplift":
            render_enterprise_uplift(hub)
        elif page == "Performance":
            render_performance_dashboard(hub)
        elif page == "Workflow Monitor":
            render_workflow_monitoring(hub)
        elif page == "Workflow Designer":
            render_workflow_designer(hub)
        elif page == "Prompt Library":
            render_prompt_library(hub)
        elif page == "Methodology Editor":
            render_methodology_editor(hub)
        elif page == "Role Manager":
            render_role_manager(hub)
        elif page == "Merge Review":
            render_merge_review(hub)
        elif page == "Documents":
            render_document_search(hub)
        elif page == "Lessons Learned":
            render_lessons_learned(hub)
        elif page == "Search":
            render_global_search(hub)
        elif page == "Marketplace":
            render_connector_marketplace(hub)
        elif page == "Project Config":
            render_project_config(hub)

    with right:
        assistant_panel(hub, outbox)


if __name__ == "__main__":
    main()

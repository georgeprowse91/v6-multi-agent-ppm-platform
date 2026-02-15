from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st

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
}


def slugify(value: str) -> str:
    return "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split()) or "unknown"


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
            stages.append(DemoStage(id=str(stage["id"]), name=str(stage["name"]), activities=stage_activities))
        methodologies.append(DemoMethodology(id=str(method["id"]), name=str(method["name"]), stages=stages))
    return methodologies


def load_conversation_scenarios() -> list[Scenario]:
    return [Scenario(id=path.stem, label=friendly_label(path.stem)) for path in sorted(CONVERSATIONS_DIR.glob("*.json"))]


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
                self._payloads[key] = json.loads((CONVERSATIONS_DIR / f"{key}.json").read_text(encoding="utf-8"))
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

    def normalized_dashboard(self) -> dict[str, Any]:
        self._record("Dashboard", ["portfolio_health", "lifecycle_metrics", "workflow_monitoring", "approvals"])
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
            rows.append({"title": item.get("title", "Untitled"), "approvers": item.get("approvers", "N/A")})
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
        return self.load("demo_seed").get("connectors", [])

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


def find_methodology(methodologies: list[DemoMethodology], method_id: str) -> DemoMethodology | None:
    return next((m for m in methodologies if m.id == method_id), None)


def find_stage(method: DemoMethodology | None, stage_id: str) -> DemoStage | None:
    if method is None:
        return None
    return next((s for s in method.stages if s.id == stage_id), None)


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

    activity = next((a for a in stage.activities if a.id == st.session_state["selected_activity_id"]), None)
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
        format_func=lambda method_id: next((m.name for m in methodologies if m.id == method_id), method_id),
    )
    sync_methodology_state(hub)

    selected_method = find_methodology(methodologies, st.session_state["selected_methodology_id"])
    stage_ids = [s.id for s in selected_method.stages]
    st.session_state["selected_stage_id"] = st.sidebar.selectbox(
        "Stage",
        stage_ids,
        index=stage_ids.index(st.session_state["selected_stage_id"]),
        format_func=lambda stage_id: next((s.name for s in selected_method.stages if s.id == stage_id), stage_id),
    )
    sync_methodology_state(hub)

    selected_stage = find_stage(selected_method, st.session_state["selected_stage_id"])
    activity_ids = [a.id for a in selected_stage.activities]
    st.session_state["selected_activity_id"] = st.sidebar.selectbox(
        "Activity",
        activity_ids,
        index=activity_ids.index(st.session_state["selected_activity_id"]),
        format_func=lambda activity_id: next((a.name for a in selected_stage.activities if a.id == activity_id), activity_id),
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


def generate_artifact_content(artifact_type: str, artifact_format: str) -> tuple[str, str]:
    project_id = st.session_state.get("selected_project") or "N/A"
    method_name = st.session_state.get("selected_methodology_name") or "N/A"
    stage_name = st.session_state.get("selected_stage_name") or "N/A"
    activity_name = st.session_state.get("selected_activity_name") or "N/A"
    outcome = st.session_state.get("selected_outcome") or "on_track"
    timestamp = datetime.now(tz=UTC).isoformat()

    if artifact_format == "csv":
        content = (
            "artifact_type,project_id,methodology,stage,activity,outcome,generated_at\n"
            f"{artifact_type},{project_id},{method_name},{stage_name},{activity_name},{outcome},{timestamp}\n"
        )
        return content, "text/csv"
    if artifact_format == "txt":
        content = (
            f"Artifact Type: {artifact_type}\n"
            f"Project: {project_id}\n"
            f"Methodology: {method_name}\n"
            f"Stage: {stage_name}\n"
            f"Activity: {activity_name}\n"
            f"Outcome: {outcome}\n"
            f"Generated: {timestamp}\n"
        )
        return content, "text/plain"

    content = (
        f"# {artifact_type.replace('_', ' ').title()}\n\n"
        f"Project: {project_id}\n"
        f"Methodology: {method_name}\n"
        f"Stage: {stage_name}\n"
        f"Activity: {activity_name}\n"
        f"Outcome: {outcome}\n"
        f"Generated: {timestamp}\n"
    )
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
        activity_id = str(payload.get("activity_id") or st.session_state.get("selected_activity_id") or "")
        if activity_id:
            st.session_state["completed_activity_ids"].add(activity_id)
            append_outbox_event(outbox, "activity.completed", {"stage_id": stage_id, "activity_id": activity_id})
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
    return [
        Chip(label="Go to Dashboard", action="NAVIGATE", payload={"page": "Dashboard"}),
        Chip(
            label="Open selected activity",
            action="OPEN_ACTIVITY",
            payload={"stage_id": st.session_state.get("selected_stage_id"), "activity_id": st.session_state.get("selected_activity_id")},
        ),
        Chip(
            label="Complete current activity",
            action="COMPLETE_ACTIVITY",
            payload={"stage_id": st.session_state.get("selected_stage_id"), "activity_id": st.session_state.get("selected_activity_id")},
        ),
        Chip(label="Generate status report", action="GENERATE_ARTIFACT", payload={"artifact_type": "status_report", "artifact_format": "md"}),
    ]


def choose_assistant_response(hub: DemoDataHub, prompt: str) -> tuple[str, str]:
    response_payload = hub.assistant_responses()
    lowered = (
        f"{prompt} "
        f"{st.session_state.get('selected_activity_name', '')} "
        f"{st.session_state.get('selected_stage_name', '')} "
        f"{st.session_state.get('selected_outcome', '')}"
    ).lower()
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


def assistant_panel(hub: DemoDataHub, outbox: DemoOutbox) -> None:
    st.subheader("Assistant")
    context_cols = st.columns(2)
    context_cols[0].markdown(f"**Project:** {st.session_state.get('selected_project') or 'Not selected'}")
    context_cols[0].markdown(f"**Stage:** {st.session_state.get('selected_stage_name') or 'Not selected'}")
    context_cols[1].markdown(f"**Activity:** {st.session_state.get('selected_activity_name') or 'Not selected'}")
    context_cols[1].markdown(f"**Status:** {st.session_state.get('selected_outcome')}")

    st.caption("Action chips")
    chip_cols = st.columns(2)
    for idx, chip in enumerate(get_action_chips()):
        if chip_cols[idx % 2].button(chip.label, key=f"chip-{idx}"):
            handle_chip(chip, outbox)
            sync_methodology_state(hub)

    st.session_state["selected_outcome"] = st.selectbox("Scenario outcome", ["on_track", "at_risk", "off_track"], index=["on_track", "at_risk", "off_track"].index(st.session_state["selected_outcome"]))

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

    prompt = st.text_area("Prompt", key="assistant_prompt")
    if st.button("Generate", use_container_width=True):
        response, provenance = choose_assistant_response(hub, prompt)
        st.session_state["assistant_messages"].append({"role": "user", "content": prompt})
        st.session_state["assistant_messages"].append({"role": "assistant", "content": response, "provenance": provenance})

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
        st.markdown(f"**{msg.get('role', 'assistant').capitalize()}:** {msg.get('content', '')}{provenance}")


def render_feature_flags_panel() -> None:
    st.sidebar.subheader("Feature Flags")
    for flag in [
        "duplicate_resolution",
        "agent_async_notifications",
        "agent_run_ui",
        "predictive_alerts",
        "multi_agent_collab",
        "multimodal_intake",
    ]:
        st.session_state["feature_flags"][flag] = st.sidebar.checkbox(flag, value=bool(st.session_state["feature_flags"].get(flag, False)))


def render_provenance(hub: DemoDataHub, view_name: str) -> None:
    st.subheader("Data provenance")
    keys = hub.provenance.get(view_name, [])
    rows = [{"dataset": key, "file": str(DATASET_FILES[key].relative_to(REPO_ROOT))} for key in keys if key in DATASET_FILES]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def render_home(hub: DemoDataHub) -> None:
    st.header("Home")
    dashboard = hub.normalized_dashboard()
    st.metric("Portfolio KPIs", len(dashboard["health"].get("kpis", [])))
    st.metric("Lifecycle gates", len(dashboard["lifecycle"].get("stage_gates", [])))
    st.metric("Workflow runs", len(dashboard["workflow"].get("runs", [])))
    render_provenance(hub, "Dashboard")


def render_workspace(hub: DemoDataHub) -> None:
    st.header("Workspace")
    projects = hub.normalized_projects()
    project_ids = [row["id"] for row in projects]
    if project_ids:
        if not st.session_state["selected_project"]:
            st.session_state["selected_project"] = project_ids[0]
        st.session_state["selected_project"] = st.selectbox("Project", project_ids, index=project_ids.index(st.session_state["selected_project"]))

    methodologies = hub.methodologies()
    selected_method = find_methodology(methodologies, st.session_state["selected_methodology_id"])
    _selected_stage = find_stage(selected_method, st.session_state["selected_stage_id"])

    st.write(
        f"Methodology: **{st.session_state['selected_methodology_name']}** | "
        f"Stage: **{st.session_state['selected_stage_name']}** | "
        f"Activity: **{st.session_state['selected_activity_name']}**"
    )

    st.dataframe(
        [
            {
                "stage_id": stage.id,
                "stage_name": stage.name,
                "activities": ", ".join(activity.name for activity in stage.activities),
            }
            for stage in selected_method.stages
        ],
        hide_index=True,
        use_container_width=True,
    )

    completed = st.session_state.get("completed_activity_ids", set())
    if completed:
        st.success(f"Completed activities: {len(completed)}")
    render_provenance(hub, "Workspace")


def render_dashboard(hub: DemoDataHub) -> None:
    st.header("Dashboard")
    data = hub.normalized_dashboard()
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
    st.header("Connectors")
    st.dataframe(hub.normalized_connectors(), hide_index=True, use_container_width=True)
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
    st.write(f"Run ID: {run_log.get('demo_run_id')}")
    st.progress(st.session_state["demo_run_step"] / max(1, len(run_log.get("agents", []))))
    if st.button("Play next agent step", use_container_width=True):
        st.session_state["demo_run_step"] = engine.play_step(st.session_state["demo_run_step"])
    if st.button("Reset run playback", use_container_width=True):
        st.session_state["demo_run_step"] = 0

    completed, queued = engine.progress(st.session_state["demo_run_step"])
    st.subheader("Completed")
    st.dataframe(completed, hide_index=True, use_container_width=True)
    st.subheader("Queued")
    st.dataframe(queued[:5], hide_index=True, use_container_width=True)
    st.subheader("Demo outbox")
    outbox_state = outbox.read()
    st.json({"demo_run_events": len(outbox_state.get("demo_run_events", [])), "assistant_actions": len(outbox_state.get("assistant_actions", [])), "audit_events": len(outbox_state.get("audit_events", []))})
    render_provenance(hub, "Demo Run")


def render_agent_runs(hub: DemoDataHub, engine: DemoRunEngine) -> None:
    st.header("Agent Runs")
    completed, queued = engine.progress(st.session_state["demo_run_step"])
    st.metric("Completed agent runs", len(completed))
    st.metric("Queued agent runs", len(queued))
    st.dataframe(completed[-10:], hide_index=True, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="PPM Standalone Demo", layout="wide")
    st.title("Standalone PPM Demo Mode")
    st.caption("Local-only mirror of web console demo mode (no backend services, no external calls).")

    hub = get_data_hub()
    init_state(hub)
    outbox = DemoOutbox(OUTBOX_PATH)
    engine = DemoRunEngine(hub.normalized_demo_run(), outbox)

    render_scenario_selectors_sidebar(hub)
    render_feature_flags_panel()

    nav_pages = ["Home", "Workspace", "Dashboard", "Approvals", "Connectors", "Audit", "Demo Run"]
    if st.session_state["feature_flags"].get("agent_async_notifications"):
        nav_pages.append("Notifications")
    if st.session_state["feature_flags"].get("agent_run_ui"):
        nav_pages.append("Agent Runs")

    if st.session_state.get("active_page") in nav_pages:
        st.session_state["selected_page"] = st.session_state["active_page"]
    st.session_state["selected_page"] = st.sidebar.radio("Navigation", nav_pages, index=nav_pages.index(st.session_state["selected_page"]) if st.session_state["selected_page"] in nav_pages else 0)
    st.session_state["active_page"] = st.session_state["selected_page"]

    left, right = st.columns([3, 2], gap="large")
    with left:
        page = st.session_state["selected_page"]
        if page == "Home":
            render_home(hub)
        elif page == "Workspace":
            render_workspace(hub)
        elif page == "Dashboard":
            render_dashboard(hub)
        elif page == "Approvals":
            render_approvals(hub)
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

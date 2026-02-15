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


@dataclass(frozen=True)
class Scenario:
    id: str
    label: str


DEMO_SCENARIOS: list[Scenario] = [
    Scenario(id="project_intake", label="Project Intake"),
    Scenario(id="resource_request", label="Resource Request"),
    Scenario(id="vendor_procurement", label="Vendor Procurement"),
]


DATASET_FILES: dict[str, Path] = {
    "projects": REPO_ROOT / "apps/web/data/projects.json",
    "demo_seed": REPO_ROOT / "apps/web/data/demo_seed.json",
    "demo_run_log": REPO_ROOT / "apps/web/data/demo/demo_run_log.json",
    "portfolio_health": REPO_ROOT / "examples/demo-scenarios/portfolio-health.json",
    "lifecycle_metrics": REPO_ROOT / "examples/demo-scenarios/lifecycle-metrics.json",
    "workflow_monitoring": REPO_ROOT / "examples/demo-scenarios/workflow-monitoring.json",
    "approvals": REPO_ROOT / "examples/demo-scenarios/approvals.json",
    "assistant_responses": REPO_ROOT / "examples/demo-scenarios/assistant-responses.json",
    "project_intake": REPO_ROOT / "apps/web/data/demo_conversations/project_intake.json",
    "resource_request": REPO_ROOT / "apps/web/data/demo_conversations/resource_request.json",
    "vendor_procurement": REPO_ROOT / "apps/web/data/demo_conversations/vendor_procurement.json",
    "feature_flags": DEMO_ROOT / "data/feature_flags_demo.json",
    "assistant_outcome_variants": DEMO_ROOT / "data/assistant_outcome_variants.json",
    "storage_notifications": REPO_ROOT / "apps/web/storage/notifications.json",
    "storage_scenarios": REPO_ROOT / "apps/web/storage/scenarios.json",
}

OUTBOX_PATH = DEMO_ROOT / "storage/demo_outbox.json"


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
            self._payloads[key] = json.loads(DATASET_FILES[key].read_text(encoding="utf-8"))
        return self._payloads[key]

    def _record(self, view: str, dataset_keys: list[str]) -> None:
        self.provenance[view] = dataset_keys

    def normalized_projects(self) -> list[dict[str, Any]]:
        self._record("Workspace", ["projects", "demo_seed", "portfolio_health"])
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

    def assistant_script(self, scenario_id: str) -> list[dict[str, str]]:
        self._record("Assistant", [scenario_id])
        return self.load(scenario_id)

    def assistant_variants(self) -> dict[str, Any]:
        return self.load("assistant_outcome_variants")


class DemoRunEngine:
    def __init__(self, run_log: dict[str, Any], outbox: DemoOutbox) -> None:
        self.run_log = run_log
        self.outbox = outbox

    def progress(self, step: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        agents = self.run_log.get("agents", [])
        completed = agents[:step]
        queued = agents[step:]
        return completed, queued

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


def init_state() -> None:
    defaults: dict[str, Any] = {
        "selected_page": "Home",
        "selected_project": None,
        "selected_stage": None,
        "selected_activity": None,
        "selected_status": "on_track",
        "selected_lifecycle_event": "generate",
        "selected_scenario": "project_intake",
        "assistant_messages": [],
        "assistant_step": 0,
        "demo_run_step": 0,
        "feature_flags": get_data_hub().feature_flags(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def lifecycle_actions(outbox: DemoOutbox) -> None:
    cols = st.columns(3)
    for event, col in zip(["generate", "review", "publish"], cols, strict=True):
        if col.button(event.capitalize(), use_container_width=True, key=f"lifecycle-{event}"):
            st.session_state["selected_lifecycle_event"] = event
            outbox.append(
                "assistant_actions",
                {
                    "event_id": f"assist-{uuid4().hex[:10]}",
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                    "event": event,
                    "project": st.session_state.get("selected_project"),
                    "stage": st.session_state.get("selected_stage"),
                    "activity": st.session_state.get("selected_activity"),
                },
            )
            st.success(f"Lifecycle action simulated: {event}")


def scenario_branch_reply(scenario: str, step: int, user_text: str) -> str | None:
    normalized = user_text.lower()
    if scenario == "project_intake" and step == 3 and "onboarding" in normalized:
        return "Great choice. I captured the objective as cutting onboarding cycle time by 30% in two quarters. Do you want me to draft an intake summary now?"
    if scenario == "resource_request" and step == 3 and "backfill" in normalized:
        return "Understood. I can prepare a hiring backfill brief with lead-time assumptions and milestone risk impact. Should I proceed?"
    if scenario == "vendor_procurement" and step == 3 and "fast" in normalized:
        return "Got it. I will optimize for fast go-live and streamline legal review checkpoints. Do you want a draft evaluation scorecard?"
    return None


def get_action_chips(flags: dict[str, bool]) -> list[str]:
    chips = ["Open dashboard", "Suggest next activity", "Generate summary"]
    if flags.get("multi_agent_collab"):
        chips.append("Shared insights")
    if flags.get("predictive_alerts"):
        chips.append("Predictive alerts")
    if flags.get("multimodal_intake"):
        chips.append("Process intake attachments")
    return chips


def add_assistant_variant_response(hub: DemoDataHub) -> None:
    variants = hub.assistant_variants().get("variants", {})
    scenario = st.session_state["selected_scenario"]
    status = st.session_state["selected_status"]
    event = st.session_state["selected_lifecycle_event"]
    activity = st.session_state.get("selected_activity") or "default"
    scenario_data = variants.get(scenario, {})
    activity_data = scenario_data.get(activity, scenario_data.get("default", {}))
    status_data = activity_data.get(status, activity_data.get("on_track", {}))
    message = status_data.get(event, status_data.get("generate", "Local demo response unavailable."))
    st.session_state["assistant_messages"].append({"role": "assistant", "content": message})


def assistant_panel(hub: DemoDataHub, outbox: DemoOutbox) -> None:
    st.subheader("Assistant")
    context_cols = st.columns(2)
    context_cols[0].markdown(f"**Project:** {st.session_state.get('selected_project') or 'Not selected'}")
    context_cols[0].markdown(f"**Stage:** {st.session_state.get('selected_stage') or 'Not selected'}")
    context_cols[1].markdown(f"**Activity:** {st.session_state.get('selected_activity') or 'Not selected'}")
    context_cols[1].markdown(f"**Status:** {st.session_state.get('selected_status')}")

    st.caption("Action chips")
    chip_cols = st.columns(2)
    chips = get_action_chips(st.session_state["feature_flags"])
    for idx, chip in enumerate(chips):
        if chip_cols[idx % 2].button(chip, key=f"chip-{idx}"):
            st.session_state["assistant_messages"].append({"role": "assistant", "content": f"Executed quick action: {chip}."})

    lifecycle_actions(outbox)

    scenario_options = [scenario.id for scenario in DEMO_SCENARIOS]
    st.session_state["selected_scenario"] = st.selectbox(
        "Assistant demo scenario",
        scenario_options,
        index=scenario_options.index(st.session_state["selected_scenario"]),
        format_func=lambda value: next(s.label for s in DEMO_SCENARIOS if s.id == value),
    )
    script = hub.assistant_script(st.session_state["selected_scenario"])

    if st.button("Restart scenario", use_container_width=True):
        st.session_state["assistant_messages"] = []
        st.session_state["assistant_step"] = 0

    if st.button("Play next step", use_container_width=True):
        step = st.session_state["assistant_step"]
        if step < len(script):
            st.session_state["assistant_messages"].append(script[step])
            st.session_state["assistant_step"] = step + 1
        else:
            st.info("Scenario complete.")

    with st.expander("Type expected response (React parity mode)"):
        user_msg = st.text_input("Send scripted message", key="assistant_user_input")
        if st.button("Send", key="assistant-send"):
            step = st.session_state["assistant_step"]
            branch = scenario_branch_reply(st.session_state["selected_scenario"], step, user_msg)
            st.session_state["assistant_messages"].append({"role": "user", "content": user_msg})
            if branch:
                st.session_state["assistant_messages"].append({"role": "assistant", "content": branch})
                st.session_state["assistant_step"] = min(step + 2, len(script))
            elif step < len(script):
                expected = script[step]
                if expected.get("role") == "user" and user_msg.lower() in expected.get("content", "").lower():
                    st.session_state["assistant_step"] = step + 1
                else:
                    st.session_state["assistant_messages"].append({"role": "assistant", "content": "For this demo script, use the suggested response path or branch alternative."})
            add_assistant_variant_response(hub)

    st.caption("Transcript")
    for msg in st.session_state["assistant_messages"]:
        st.markdown(f"**{msg.get('role', 'assistant').capitalize()}:** {msg.get('content', '')}")


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
    rows = []
    for key in keys:
        path = DATASET_FILES[key]
        rows.append({"dataset": key, "file": str(path.relative_to(REPO_ROOT if path.is_relative_to(REPO_ROOT) else DEMO_ROOT.parent))})
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
    if not st.session_state["selected_project"]:
        st.session_state["selected_project"] = project_ids[0]
    st.session_state["selected_project"] = st.selectbox("Project", project_ids, index=project_ids.index(st.session_state["selected_project"]))

    lifecycle = hub.normalized_dashboard()["lifecycle"]
    stages = lifecycle.get("stage_gates", [])
    stage_ids = [stage.get("stage_name", "Unknown") for stage in stages]
    st.session_state["selected_stage"] = st.selectbox("Stage", stage_ids, index=0 if st.session_state["selected_stage"] not in stage_ids else stage_ids.index(st.session_state["selected_stage"]))

    activity_options = ["Define scope", "Review dependencies", "Prepare approval packet", "Publish artifact"]
    st.session_state["selected_activity"] = st.selectbox("Activity", activity_options, index=0 if st.session_state["selected_activity"] not in activity_options else activity_options.index(st.session_state["selected_activity"]))
    st.session_state["selected_status"] = st.selectbox("Scenario outcome", ["on_track", "at_risk", "off_track"], index=["on_track", "at_risk", "off_track"].index(st.session_state["selected_status"]))

    st.dataframe(stages, hide_index=True, use_container_width=True)
    if st.session_state["feature_flags"].get("multi_agent_collab"):
        st.info("Shared insights are enabled for workspace collaboration.")
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
    if st.session_state["feature_flags"].get("duplicate_resolution"):
        st.info("Duplicate resolution route is demo-enabled.")
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

    init_state()
    hub = get_data_hub()
    outbox = DemoOutbox(OUTBOX_PATH)
    engine = DemoRunEngine(hub.normalized_demo_run(), outbox)

    render_feature_flags_panel()

    nav_pages = ["Home", "Workspace", "Dashboard", "Approvals", "Connectors", "Audit", "Demo Run"]
    if st.session_state["feature_flags"].get("agent_async_notifications"):
        nav_pages.append("Notifications")
    if st.session_state["feature_flags"].get("agent_run_ui"):
        nav_pages.append("Agent Runs")

    st.session_state["selected_page"] = st.sidebar.radio("Navigation", nav_pages, index=nav_pages.index(st.session_state["selected_page"]) if st.session_state["selected_page"] in nav_pages else 0)

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

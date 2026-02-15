from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st
from pydantic import BaseModel


class ProjectSummary(BaseModel):
    id: str
    name: str
    status: str = "In Progress"
    owner: str = "Demo Owner"
    source: str


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_FILES = {
    "projects": REPO_ROOT / "apps/web/data/projects.json",
    "demo_seed": REPO_ROOT / "apps/web/data/demo_seed.json",
    "demo_run_log": REPO_ROOT / "apps/web/data/demo/demo_run_log.json",
    "health": REPO_ROOT / "examples/demo-scenarios/portfolio-health.json",
    "schedule": REPO_ROOT / "examples/demo-scenarios/schedule.json",
    "wbs": REPO_ROOT / "examples/demo-scenarios/wbs.json",
    "approvals": REPO_ROOT / "examples/demo-scenarios/approvals.json",
    "assistant_responses": REPO_ROOT / "examples/demo-scenarios/assistant-responses.json",
    "project_conversation": REPO_ROOT / "apps/web/data/demo_conversations/project_intake.json",
    "project_health": REPO_ROOT / "apps/web/data/demo_dashboards/project-dashboard-health.json",
    "project_risks": REPO_ROOT / "apps/web/data/demo_dashboards/project-dashboard-risks.json",
    "project_issues": REPO_ROOT / "apps/web/data/demo_dashboards/project-dashboard-issues.json",
    "project_narrative": REPO_ROOT / "apps/web/data/demo_dashboards/project-dashboard-narrative.json",
    "storage_scenarios": REPO_ROOT / "apps/web/storage/scenarios.json",
    "storage_notifications": REPO_ROOT / "apps/web/storage/notifications.json",
}


@st.cache_data(show_spinner=False)
def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data(show_spinner=False)
def collect_demo_projects() -> list[ProjectSummary]:
    projects: list[ProjectSummary] = []

    for item in load_json(DATA_FILES["projects"]).get("projects", []):
        projects.append(
            ProjectSummary(
                id=item.get("id", item.get("project_id", "unknown-project")),
                name=item.get("name", item.get("title", "Untitled project")),
                status=item.get("status", "In Progress"),
                owner=item.get("owner", "Demo Owner"),
                source="apps/web/data/projects.json",
            )
        )

    demo_seed = load_json(DATA_FILES["demo_seed"])
    for portfolio in demo_seed.get("portfolios", []):
        data = portfolio.get("data", {})
        projects.append(
            ProjectSummary(
                id=data.get("portfolio_id", "portfolio-demo"),
                name=portfolio.get("title", "Portfolio program"),
                status=portfolio.get("status", "active"),
                owner="PMO",
                source="apps/web/data/demo_seed.json",
            )
        )

    scenario_health = load_json(DATA_FILES["health"])
    projects.append(
        ProjectSummary(
            id=scenario_health.get("project_id", "demo-1"),
            name="Portfolio Modernisation Demo",
            status="On Track",
            owner="A. Lee",
            source="examples/demo-scenarios/portfolio-health.json",
        )
    )

    dashboard_health = load_json(DATA_FILES["project_health"])
    projects.append(
        ProjectSummary(
            id=dashboard_health.get("project_id", "project-alpha"),
            name="Project Alpha",
            status=dashboard_health.get("status", "In Progress"),
            owner="Delivery PMO",
            source="apps/web/data/demo_dashboards/project-dashboard-health.json",
        )
    )

    deduped: dict[str, ProjectSummary] = {}
    for project in projects:
        deduped[project.id] = project
    return sorted(deduped.values(), key=lambda project: project.name.lower())


def render_dashboard(projects: list[ProjectSummary]) -> None:
    st.subheader("Dashboard")
    health = load_json(DATA_FILES["health"])
    approvals = load_json(DATA_FILES["approvals"])
    demo_run_log = load_json(DATA_FILES["demo_run_log"])
    kpis = health.get("kpis", [])
    scenarios = load_json(DATA_FILES["storage_scenarios"]).get("scenarios", [])
    notifications = load_json(DATA_FILES["storage_notifications"]).get("history", [])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Projects", len(projects))
    c2.metric("KPIs tracked", len(kpis))
    c3.metric("Pending approvals", approvals.get("pending_count", 0))
    c4.metric("Agents exercised", demo_run_log.get("total_agents_executed", 0))

    st.caption(f"Portfolio: {health.get('portfolio_id', 'demo-portfolio')} • As of {health.get('as_of', 'n/a')}")
    st.dataframe(kpis, use_container_width=True, hide_index=True)
    st.caption(f"Scenario templates loaded: {len(scenarios)} • Stored notifications loaded: {len(notifications)}")


def render_project_list(projects: list[ProjectSummary]) -> ProjectSummary:
    st.subheader("Project list")
    st.dataframe([project.model_dump() for project in projects], use_container_width=True, hide_index=True)
    selected_id = st.selectbox("Select a project", options=[project.id for project in projects], index=0)
    return next(project for project in projects if project.id == selected_id)


def render_project_detail(selected_project: ProjectSummary) -> None:
    st.subheader("Sample project detail")
    st.markdown(f"**{selected_project.name}** (`{selected_project.id}`)")
    st.markdown(f"Status: `{selected_project.status}` • Owner: `{selected_project.owner}`")

    schedule = load_json(DATA_FILES["schedule"]).get("tasks", [])
    wbs_items = load_json(DATA_FILES["wbs"]).get("items", [])
    dashboard_health = load_json(DATA_FILES["project_health"])
    risks = load_json(DATA_FILES["project_risks"]).get("items", [])
    issues = load_json(DATA_FILES["project_issues"]).get("items", [])
    narrative = load_json(DATA_FILES["project_narrative"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Schedule tasks", len(schedule))
    c2.metric("WBS entries", len(wbs_items))
    c3.metric("Composite score", dashboard_health.get("composite_score", "n/a"))

    with st.expander("Narrative summary", expanded=True):
        st.write(narrative.get("summary", "No summary available."))
        for line in narrative.get("highlights", []):
            st.markdown(f"- {line}")

    with st.expander("Top risks"):
        st.dataframe(risks, use_container_width=True, hide_index=True)

    with st.expander("Open issues"):
        st.dataframe(issues, use_container_width=True, hide_index=True)

    with st.expander("Schedule"):
        st.dataframe(schedule, use_container_width=True, hide_index=True)


def render_assistant_panel() -> None:
    st.subheader("Assistant panel (mock)")
    st.caption("This interaction is local-only and uses bundled demo conversation files.")

    canned_conversation = load_json(DATA_FILES["project_conversation"])
    canned_responses = load_json(DATA_FILES["assistant_responses"])

    prompt = st.text_input("Ask the assistant", value="Draft an intake summary for a customer self-service portal.")
    if st.button("Generate mock response", type="primary"):
        response_text = canned_responses.get("default", {}).get("summary", "Demo response unavailable")
        st.success("Mock response generated from local JSON data.")
        st.markdown(f"**Prompt**: {prompt}")
        st.markdown(f"**Assistant**: {response_text}")

    with st.expander("Sample transcript"):
        for message in canned_conversation:
            st.markdown(f"**{message.get('role', 'assistant').capitalize()}:** {message.get('content', '')}")


def render_data_overview() -> None:
    st.subheader("Loaded data sources")
    records = []
    for name, path in DATA_FILES.items():
        payload = load_json(path)
        rows = len(payload) if isinstance(payload, list) else len(payload.keys()) if isinstance(payload, dict) else 1
        records.append({"dataset": name, "path": str(path.relative_to(REPO_ROOT)), "type": type(payload).__name__, "top_level_items": rows})
    st.dataframe(records, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="PPM Standalone Demo", layout="wide")
    st.title("Standalone PPM Demo Mode")
    st.write("Run a no-Docker, no-backend Streamlit demo using static scenario data from the repository.")

    projects = collect_demo_projects()
    if not projects:
        st.error("No project-like demo records were found in local JSON files.")
        return

    tab_dashboard, tab_projects, tab_assistant = st.tabs(["Dashboard", "Projects", "Assistant"])

    with tab_dashboard:
        render_dashboard(projects)
        render_data_overview()

    with tab_projects:
        selected_project = render_project_list(projects)
        render_project_detail(selected_project)

    with tab_assistant:
        render_assistant_panel()

    st.divider()
    st.caption("No external HTTP calls are made by this demo app.")


if __name__ == "__main__":
    main()

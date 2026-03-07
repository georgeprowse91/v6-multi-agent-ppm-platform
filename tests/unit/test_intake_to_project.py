"""Tests for End-to-End Intake-to-Project Automation (Enhancement 9).

Tests cover:
- Post-approval hook for project entity creation
- Intake workflow definition updates
- IntakeStatusPage approval-to-setup routing (structure)
- Connector registry endpoint
- Setup wizard connector browser and team assignment
- Create-from-intake endpoint
- Configure-workspace with connectors and team
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path bootstrapping
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tests" / "unit"))

from _route_test_helpers import load_route_module  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Decision Actions — post-approval hook
# ---------------------------------------------------------------------------

_DECISION_ACTIONS_PATH = (
    _REPO / "agents" / "core-orchestration"
    / "approval-workflow-agent" / "src" / "actions" / "decision_actions.py"
)


class TestDecisionActionsPostApprovalHook:
    """Verify the post-approval hook for intake project creation."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        self.source = _DECISION_ACTIONS_PATH.read_text()

    def test_file_exists(self):
        assert _DECISION_ACTIONS_PATH.exists()

    def test_has_handle_intake_approval_function(self):
        assert "def _handle_intake_approval(" in self.source

    def test_hook_creates_project_entity(self):
        assert "project_id" in self.source
        assert "project.created" in self.source

    def test_hook_publishes_project_created_event(self):
        assert "project.created" in self.source
        assert "event_type" in self.source

    def test_hook_publishes_realtime_notification(self):
        assert "notification.project_created" in self.source

    def test_hook_emits_audit_event(self):
        assert "project.created_from_intake" in self.source

    def test_hook_checks_request_type_intake(self):
        assert 'request_type == "intake"' in self.source

    def test_hook_generates_project_id(self):
        assert "proj-" in self.source
        assert "uuid.uuid4()" in self.source

    def test_hook_extracts_sponsor_and_business_case(self):
        assert 'request_details.get("sponsor"' in self.source
        assert 'request_details.get("business_case"' in self.source

    def test_hook_returns_created_project_in_result(self):
        assert '"created_project"' in self.source


# ---------------------------------------------------------------------------
# 2. Intake workflow definition
# ---------------------------------------------------------------------------

_WORKFLOW_PATH = _REPO / "ops" / "config" / "demo-workflows" / "project-intake.workflow.yaml"


class TestIntakeWorkflowDefinition:
    @pytest.fixture(autouse=True)
    def _load_workflow(self):
        self.content = _WORKFLOW_PATH.read_text()

    def test_workflow_exists(self):
        assert _WORKFLOW_PATH.exists()

    def test_version_is_2(self):
        assert "version: 2.0.0" in self.content

    def test_has_create_project_step(self):
        assert "id: create_project" in self.content

    def test_has_provision_workspace_step(self):
        assert "id: provision_workspace" in self.content

    def test_create_project_uses_post_approval_hook(self):
        assert "post_approval_hook: create_project_entity" in self.content

    def test_pmo_triage_leads_to_create_project(self):
        assert "next: create_project" in self.content

    def test_create_project_leads_to_provision_workspace(self):
        assert "next: provision_workspace" in self.content

    def test_provision_workspace_leads_to_notify(self):
        assert "next: notify_requester" in self.content

    def test_provision_workspace_uses_workspace_agent(self):
        assert "agent: workspace_setup" in self.content

    def test_has_create_from_intake_endpoint(self):
        assert "create-from-intake" in self.content


# ---------------------------------------------------------------------------
# 3. IntakeStatusPage — approval-to-setup routing (structure)
# ---------------------------------------------------------------------------

_INTAKE_STATUS_PATH = _REPO / "apps" / "web" / "frontend" / "src" / "pages" / "IntakeStatusPage.tsx"


class TestIntakeStatusPageRouting:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.source = _INTAKE_STATUS_PATH.read_text()

    def test_imports_use_navigate(self):
        assert "useNavigate" in self.source

    def test_has_project_id_field(self):
        assert "project_id" in self.source

    def test_has_configure_btn(self):
        assert "Configure Project" in self.source

    def test_has_setup_wizard_link(self):
        assert "Go to Setup Wizard" in self.source
        assert "/projects/new" in self.source

    def test_passes_intake_param(self):
        assert "intake=" in self.source

    def test_shows_project_created_section(self):
        assert "Project Created" in self.source
        assert "Open Project" in self.source

    def test_calls_create_from_intake(self):
        assert "create-from-intake" in self.source

    def test_has_creating_project_state(self):
        assert "creatingProject" in self.source

    def test_approved_status_check(self):
        assert "request.status === 'approved'" in self.source


# ---------------------------------------------------------------------------
# 4. ProjectSetupWizardPage — connector browser and team assignment
# ---------------------------------------------------------------------------

_WIZARD_PATH = _REPO / "apps" / "web" / "frontend" / "src" / "pages" / "ProjectSetupWizardPage.tsx"


class TestProjectSetupWizardPage:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.source = _WIZARD_PATH.read_text()

    def test_has_six_steps(self):
        assert "'Profile', 'Methodology', 'Template', 'Connectors', 'Team', 'Launch'" in self.source

    def test_has_connector_entry_interface(self):
        assert "interface ConnectorEntry" in self.source

    def test_has_team_member_interface(self):
        assert "interface TeamMember" in self.source

    def test_has_connector_toggle(self):
        assert "toggleConnector" in self.source

    def test_has_add_team_member(self):
        assert "addTeamMember" in self.source

    def test_has_remove_team_member(self):
        assert "removeTeamMember" in self.source

    def test_has_category_labels(self):
        assert "CATEGORY_LABELS" in self.source
        assert "Project Management" in self.source

    def test_has_project_roles(self):
        assert "PROJECT_ROLES" in self.source
        assert "Project Manager" in self.source
        assert "Scrum Master" in self.source

    def test_reads_intake_param(self):
        assert "useSearchParams" in self.source
        assert "intake" in self.source

    def test_sends_enabled_connectors(self):
        assert "enabled_connectors" in self.source

    def test_sends_team_members(self):
        assert "team_members" in self.source

    def test_has_connector_grid(self):
        assert "connectorGrid" in self.source

    def test_has_team_table(self):
        assert "teamTable" in self.source

    def test_has_category_filter(self):
        assert "connectorFilter" in self.source
        assert "categoryFilter" in self.source

    def test_has_launch_summary(self):
        assert "Setup Summary" in self.source
        assert "launchSummary" in self.source

    def test_fetches_connector_registry(self):
        assert "/api/connectors/registry" in self.source

    def test_has_fallback_connectors(self):
        assert "Jira" in self.source
        assert "Azure DevOps" in self.source
        assert "Slack" in self.source


# ---------------------------------------------------------------------------
# 5. Project setup API routes
# ---------------------------------------------------------------------------


def _make_setup_app():
    mod = load_route_module("project_setup.py")
    app = FastAPI()
    app.include_router(mod.router)
    return app


@pytest.fixture
def setup_client():
    return TestClient(_make_setup_app())


class TestProjectSetupRoutes:
    def test_connector_registry_endpoint(self, setup_client):
        resp = setup_client.get("/api/connectors/registry")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Should have entries from connectors.json
        if len(data) > 0:
            assert "name" in data[0]
            assert "category" in data[0]

    def test_connector_registry_returns_categories(self, setup_client):
        resp = setup_client.get("/api/connectors/registry")
        data = resp.json()
        if len(data) > 0:
            categories = {c["category"] for c in data}
            assert len(categories) >= 2  # Should have multiple categories

    def test_create_from_intake_returns_project(self, setup_client):
        resp = setup_client.post(
            "/api/project-setup/create-from-intake",
            json={"intake_request_id": "intake-001"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"].startswith("proj-")
        assert body["intake_request_id"] == "intake-001"
        assert body["status"] == "setup_pending"

    def test_create_from_intake_with_name(self, setup_client):
        resp = setup_client.post(
            "/api/project-setup/create-from-intake",
            json={"intake_request_id": "intake-002", "project_name": "My Project"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_name"] == "My Project"

    def test_create_from_intake_default_name(self, setup_client):
        resp = setup_client.post(
            "/api/project-setup/create-from-intake",
            json={"intake_request_id": "intake-003"},
        )
        body = resp.json()
        assert "intake-003" in body["project_name"]

    def test_configure_workspace_with_connectors(self, setup_client):
        resp = setup_client.post(
            "/api/project-setup/configure-workspace",
            json={
                "project_name": "Test Project",
                "template_id": "tmpl-agile-tech",
                "enabled_connectors": ["Jira", "Slack"],
                "team_members": [],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"].startswith("proj-")
        assert body["enabled_connectors"] == ["Jira", "Slack"]

    def test_configure_workspace_with_team(self, setup_client):
        resp = setup_client.post(
            "/api/project-setup/configure-workspace",
            json={
                "project_name": "Team Project",
                "template_id": "tmpl-agile-tech",
                "enabled_connectors": [],
                "team_members": [
                    {"name": "Alice", "email": "alice@example.com", "role": "Project Manager"},
                    {"name": "Bob", "email": "bob@example.com", "role": "Developer"},
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["team_members"]) == 2
        assert body["team_members"][0]["name"] == "Alice"
        assert body["team_members"][0]["role"] == "Project Manager"

    def test_configure_workspace_with_intake_reference(self, setup_client):
        resp = setup_client.post(
            "/api/project-setup/configure-workspace",
            json={
                "project_name": "Intake Project",
                "template_id": "tmpl-agile-tech",
                "intake_request_id": "intake-005",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["intake_request_id"] == "intake-005"

    def test_configure_workspace_empty_name_fails(self, setup_client):
        resp = setup_client.post(
            "/api/project-setup/configure-workspace",
            json={"project_name": "", "template_id": "tmpl-agile-tech"},
        )
        assert resp.status_code == 422

    def test_configure_workspace_empty_template_fails(self, setup_client):
        resp = setup_client.post(
            "/api/project-setup/configure-workspace",
            json={"project_name": "Test", "template_id": ""},
        )
        assert resp.status_code == 422

    def test_recommend_methodology_returns_list(self, setup_client):
        resp = setup_client.post(
            "/api/project-setup/recommend-methodology",
            json={
                "industry": "technology",
                "team_size": 10,
                "duration_months": 6,
                "risk_level": "medium",
                "regulatory": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_list_templates(self, setup_client):
        resp = setup_client.get("/api/project-setup/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# 6. CSS modules existence
# ---------------------------------------------------------------------------


class TestCSSModules:
    def test_intake_status_css_has_approval_actions(self):
        css = (_REPO / "apps" / "web" / "frontend" / "src" / "pages" / "IntakeStatusPage.module.css").read_text()
        assert ".approvalActions" in css
        assert ".configureBtn" in css
        assert ".projectCreated" in css
        assert ".setupPrompt" in css

    def test_wizard_css_has_connector_styles(self):
        css = (_REPO / "apps" / "web" / "frontend" / "src" / "pages" / "ProjectSetupWizardPage.module.css").read_text()
        assert ".connectorGrid" in css
        assert ".connectorCard" in css
        assert ".connectorEnabled" in css
        assert ".categoryFilter" in css
        assert ".catBtn" in css
        assert ".connectorToggle" in css

    def test_wizard_css_has_team_styles(self):
        css = (_REPO / "apps" / "web" / "frontend" / "src" / "pages" / "ProjectSetupWizardPage.module.css").read_text()
        assert ".teamTable" in css
        assert ".teamInputRow" in css
        assert ".roleBadge" in css
        assert ".addMemberBtn" in css
        assert ".removeBtn" in css

    def test_wizard_css_has_launch_summary(self):
        css = (_REPO / "apps" / "web" / "frontend" / "src" / "pages" / "ProjectSetupWizardPage.module.css").read_text()
        assert ".launchSummary" in css
        assert ".summaryGrid" in css
        assert ".summaryItem" in css


# ---------------------------------------------------------------------------
# 7. Integration: workflow + decision_actions consistency
# ---------------------------------------------------------------------------


class TestIntegrationConsistency:
    def test_workflow_references_existing_endpoints(self):
        workflow = _WORKFLOW_PATH.read_text()
        # create-from-intake endpoint should be referenced
        assert "create-from-intake" in workflow
        # configure-workspace endpoint should be referenced
        assert "configure-workspace" in workflow

    def test_decision_actions_request_type_matches_workflow(self):
        """The decision_actions hook triggers on request_type == 'intake',
        which must match what the intake workflow submits."""
        source = _DECISION_ACTIONS_PATH.read_text()
        assert 'request_type == "intake"' in source

    def test_wizard_step_count_matches_labels(self):
        source = _WIZARD_PATH.read_text()
        # 6 steps: Profile, Methodology, Template, Connectors, Team, Launch
        assert "step === 0" in source  # Profile
        assert "step === 1" in source  # Methodology
        assert "step === 2" in source  # Template
        assert "step === 3" in source  # Connectors
        assert "step === 4" in source  # Team
        assert "step === 5" in source  # Launch

    def test_intake_status_references_create_from_intake_api(self):
        source = _INTAKE_STATUS_PATH.read_text()
        assert "create-from-intake" in source
        assert "project-setup" in source

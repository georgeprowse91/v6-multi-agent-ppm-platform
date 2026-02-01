import pytest
from quality_management_agent import QualityManagementAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class DummyApprovalAgent:
    async def process(self, payload: dict) -> dict:
        return {"status": "approved", "approval_id": "ap-42", "approver": "qa-lead"}


class DummyCalendarClient:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def create_event(self, event: dict) -> dict:
        record = {"event_id": f"cal-{event['review_id']}", "status": "scheduled"}
        self.events.append(record)
        return record


@pytest.mark.asyncio
async def test_quality_management_persists_and_emits_events(tmp_path):
    event_bus = EventCollector()
    agent = QualityManagementAgent(
        config={
            "event_bus": event_bus,
            "quality_plan_store_path": tmp_path / "plans.json",
            "test_case_store_path": tmp_path / "cases.json",
            "defect_store_path": tmp_path / "defects.json",
            "audit_store_path": tmp_path / "audits.json",
        }
    )
    await agent.initialize()

    plan_response = await agent.process(
        {
            "action": "create_quality_plan",
            "tenant_id": "tenant-q",
            "plan": {"project_id": "project-1", "objectives": ["zero defects"]},
        }
    )
    assert agent.quality_plan_store.get("tenant-q", plan_response["plan_id"])

    approval_response = await agent.process(
        {
            "action": "approve_quality_plan",
            "tenant_id": "tenant-q",
            "plan_id": plan_response["plan_id"],
            "approver": "qa-lead",
        }
    )
    assert approval_response["status"] == "Approved"

    test_case_response = await agent.process(
        {
            "action": "create_test_case",
            "tenant_id": "tenant-q",
            "test_case": {
                "project_id": "project-1",
                "name": "Login test",
                "steps": ["Open login", "Enter credentials"],
                "expected_results": "User logged in",
            },
        }
    )
    suite_response = await agent.process(
        {
            "action": "create_test_suite",
            "test_suite": {
                "project_id": "project-1",
                "name": "Regression",
                "test_case_ids": [test_case_response["test_case_id"]],
            },
        }
    )
    execution_response = await agent.process(
        {
            "action": "execute_tests",
            "tenant_id": "tenant-q",
            "test_execution": {
                "project_id": "project-1",
                "suite_id": suite_response["suite_id"],
                "execution_mode": "playwright",
                "auto_log_defects": False,
            },
        }
    )
    assert execution_response["artifact_blob"]["uri"].startswith("https://blob.local/")

    defect_response = await agent.process(
        {
            "action": "log_defect",
            "tenant_id": "tenant-q",
            "defect": {"summary": "Login fails", "severity": "high", "component": "auth"},
        }
    )
    assert agent.defect_store.get("tenant-q", defect_response["defect_id"])

    audit_response = await agent.process(
        {
            "action": "conduct_audit",
            "tenant_id": "tenant-q",
            "audit": {"project_id": "project-1", "title": "Sprint audit"},
        }
    )
    assert agent.audit_store.get("tenant-q", audit_response["audit_id"])
    assert any(topic == "quality.plan.created" for topic, _ in event_bus.events)
    assert any(topic == "quality.plan.approved" for topic, _ in event_bus.events)
    assert any(topic == "quality.test_execution.completed" for topic, _ in event_bus.events)
    assert any(topic == "quality.defect.logged" for topic, _ in event_bus.events)
    assert any(topic == "quality.audit.completed" for topic, _ in event_bus.events)


@pytest.mark.asyncio
async def test_quality_plan_auto_approval_updates_status(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "approval_agent": DummyApprovalAgent(),
            "quality_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "create_quality_plan",
            "tenant_id": "tenant-q",
            "plan": {"project_id": "project-1", "objectives": ["shift-left testing"]},
        }
    )

    assert response["status"] == "Approved"
    assert response["approval"]["approval_id"] == "ap-42"


@pytest.mark.asyncio
async def test_quality_management_dashboard_success(tmp_path):
    event_bus = EventCollector()
    agent = QualityManagementAgent(
        config={
            "event_bus": event_bus,
            "quality_plan_store_path": tmp_path / "plans.json",
            "defect_store_path": tmp_path / "defects.json",
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_quality_dashboard", "tenant_id": "tenant-q"})

    assert "defect_statistics" in response


@pytest.mark.asyncio
async def test_quality_management_release_notes_report(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "quality_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "generate_quality_report",
            "report_type": "release_notes",
            "filters": {"project_id": "project-1"},
        }
    )

    assert response["report_type"] == "release_notes"
    assert "narrative" in response["data"]


@pytest.mark.asyncio
async def test_quality_management_validation_rejects_invalid_action(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "quality_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_quality_management_validation_rejects_missing_fields(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "quality_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input(
        {"action": "create_quality_plan", "plan": {"project_id": "X"}}
    )

    assert valid is False


@pytest.mark.asyncio
async def test_quality_management_requirement_linking(tmp_path):
    event_bus = EventCollector()
    agent = QualityManagementAgent(
        config={
            "event_bus": event_bus,
            "quality_plan_store_path": tmp_path / "plans.json",
            "test_case_store_path": tmp_path / "cases.json",
            "requirement_link_store_path": tmp_path / "links.json",
            "project_definition": {
                "requirements_by_project": {"project-1": [{"id": "REQ-1", "title": "Login"}]}
            },
        }
    )
    await agent.initialize()

    test_case_response = await agent.process(
        {
            "action": "create_test_case",
            "tenant_id": "tenant-q",
            "test_case": {
                "project_id": "project-1",
                "name": "Login test",
                "requirement_ids": ["REQ-1", "REQ-2"],
            },
        }
    )

    link_response = await agent.process(
        {
            "action": "link_test_case_requirements",
            "tenant_id": "tenant-q",
            "link": {
                "project_id": "project-1",
                "test_case_id": test_case_response["test_case_id"],
                "requirement_ids": ["REQ-1", "REQ-2"],
            },
        }
    )
    assert link_response["status"] == "linked"
    assert any(req["status"] == "validated" for req in link_response["requirements"])

    updated_link = await agent.process(
        {
            "action": "update_test_case_links",
            "link_id": link_response["link_id"],
            "updates": {"requirement_ids": ["REQ-1"]},
        }
    )
    assert len(updated_link["requirements"]) == 1

    query_response = await agent.process(
        {
            "action": "get_requirement_links",
            "tenant_id": "tenant-q",
            "filters": {"test_case_id": test_case_response["test_case_id"]},
        }
    )
    assert query_response["count"] >= 1


@pytest.mark.asyncio
async def test_quality_management_defect_sync_and_assignment(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "defect_store_path": tmp_path / "defects.json",
            "resource_capacity": {
                "candidates": [
                    {"resource_id": "eng-1", "skills": ["auth", "code_defect"], "availability": 0.9}
                ]
            },
            "jira": {"enabled": True},
            "azure_devops": {"enabled": True},
        }
    )
    await agent.initialize()

    defect_response = await agent.process(
        {
            "action": "log_defect",
            "tenant_id": "tenant-q",
            "defect": {
                "project_id": "project-1",
                "summary": "Auth failure",
                "severity": "high",
                "component": "auth",
            },
        }
    )
    assert defect_response["assigned_to"] == "eng-1"

    updated = await agent.process(
        {
            "action": "update_defect",
            "defect_id": defect_response["defect_id"],
            "updates": {"external_updates": {"jira": {"status": "Resolved"}}},
        }
    )
    assert updated["status"] == "Resolved"


@pytest.mark.asyncio
async def test_quality_management_root_cause_and_recommendations(tmp_path):
    agent = QualityManagementAgent(
        config={"event_bus": EventCollector(), "defect_store_path": tmp_path / "defects.json"}
    )
    await agent.initialize()

    defect_ids = []
    for idx in range(3):
        response = await agent.process(
            {
                "action": "log_defect",
                "tenant_id": "tenant-q",
                "defect": {
                    "project_id": "project-1",
                    "summary": f"Defect {idx}",
                    "severity": "medium",
                    "component": "api",
                },
            }
        )
        defect_ids.append(response["defect_id"])

    rca_response = await agent.process(
        {"action": "perform_root_cause_analysis", "defect_ids": defect_ids}
    )
    assert rca_response["refactoring_recommendations"]


@pytest.mark.asyncio
async def test_quality_management_end_to_end_defect_lifecycle(tmp_path):
    event_bus = EventCollector()
    agent = QualityManagementAgent(
        config={
            "event_bus": event_bus,
            "test_case_store_path": tmp_path / "cases.json",
            "defect_store_path": tmp_path / "defects.json",
            "audit_store_path": tmp_path / "audits.json",
            "ci_pipelines": {
                "pipelines": {
                    "pipeline-1": {
                        "test_results": [
                            {"test_case_id": "TC-1", "name": "Test 1", "result": "fail"}
                        ]
                    }
                },
                "coverage_by_project": {"project-1": {"coverage_pct": 78.0}},
            },
        }
    )
    await agent.initialize()

    test_case_response = await agent.process(
        {
            "action": "create_test_case",
            "tenant_id": "tenant-q",
            "test_case": {
                "project_id": "project-1",
                "name": "API test",
                "steps": ["Call endpoint"],
                "expected_results": "200 OK",
            },
        }
    )
    suite_response = await agent.process(
        {
            "action": "create_test_suite",
            "test_suite": {
                "project_id": "project-1",
                "name": "CI Suite",
                "test_case_ids": [test_case_response["test_case_id"]],
            },
        }
    )
    execution_response = await agent.process(
        {
            "action": "execute_tests",
            "tenant_id": "tenant-q",
            "test_execution": {
                "project_id": "project-1",
                "suite_id": suite_response["suite_id"],
                "execution_mode": "ci",
                "ci_pipeline_id": "pipeline-1",
                "auto_log_defects": True,
            },
        }
    )
    assert execution_response["failed"] == 1
    assert execution_response["coverage_snapshot"]["coverage_pct"] == 78.0


@pytest.mark.asyncio
async def test_quality_management_devops_and_ci_sync(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "test_case_store_path": tmp_path / "cases.json",
            "azure_devops": {"enabled": True, "plan_id": "plan-99", "suite_id": "suite-99"},
            "ci_pipelines": {
                "github_actions": {
                    "pipelines": {
                        "gha-1": {
                            "test_results": [
                                {"test_case_id": "TC-1", "name": "Unit", "result": "pass"}
                            ]
                        }
                    },
                    "coverage_by_project": {"project-1": {"coverage_pct": 92.5}},
                }
            },
        }
    )
    await agent.initialize()

    test_case_response = await agent.process(
        {
            "action": "create_test_case",
            "tenant_id": "tenant-q",
            "test_case": {"project_id": "project-1", "name": "Unit test"},
        }
    )
    assert test_case_response["sync_status"]["external_refs"]["azure_devops"]["plan_id"] == "plan-99"

    suite_response = await agent.process(
        {
            "action": "create_test_suite",
            "test_suite": {
                "project_id": "project-1",
                "name": "GHA suite",
                "test_case_ids": [test_case_response["test_case_id"]],
            },
        }
    )
    execution_response = await agent.process(
        {
            "action": "execute_tests",
            "tenant_id": "tenant-q",
            "test_execution": {
                "project_id": "project-1",
                "suite_id": suite_response["suite_id"],
                "execution_mode": "ci",
                "ci_pipeline_id": "gha-1",
                "ci_provider": "github_actions",
            },
        }
    )
    assert execution_response["code_coverage"] == 92.5
    assert execution_response["sync_status"]["external_refs"]["azure_devops"]["run_id"].startswith(
        "ado-run-"
    )


@pytest.mark.asyncio
async def test_quality_management_ml_classification_and_audit_schedule(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "calendar_client": DummyCalendarClient(),
            "defect_store_path": tmp_path / "defects.json",
            "audit_store_path": tmp_path / "audits.json",
        }
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "log_defect",
            "tenant_id": "tenant-q",
            "defect": {
                "project_id": "project-1",
                "summary": "Slow response in API",
                "severity": "high",
                "component": "api",
            },
        }
    )
    response = await agent.process(
        {
            "action": "log_defect",
            "tenant_id": "tenant-q",
            "defect": {
                "project_id": "project-1",
                "summary": "Latency spike on login",
                "component": "auth",
            },
        }
    )
    assert response["auto_classification"]["model"] == "token_frequency"

    review_response = await agent.process(
        {
            "action": "schedule_review",
            "review": {
                "project_id": "project-1",
                "title": "Code review",
                "participants": ["qa-lead"],
                "scheduled_date": "2025-01-10T10:00:00",
            },
        }
    )
    assert review_response["calendar_event"]["status"] == "scheduled"


@pytest.mark.asyncio
async def test_quality_management_metrics_include_code_size(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "defect_store_path": tmp_path / "defects.json",
            "code_repos": {"size_by_project": {"project-1": {"loc": 12000, "function_points": 60}}},
        }
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "log_defect",
            "tenant_id": "tenant-q",
            "defect": {
                "project_id": "project-1",
                "summary": "Calculation bug",
                "severity": "medium",
                "component": "billing",
            },
        }
    )

    metrics = await agent.process({"action": "calculate_metrics", "project_id": "project-1"})
    assert metrics["code_size_metrics"]["loc"] == 12000
    assert metrics["defect_density_per_function_point"] is not None

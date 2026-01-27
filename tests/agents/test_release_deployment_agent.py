import pytest
from release_deployment_agent import ReleaseDeploymentAgent


class ApprovalStub:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"approval_id": "appr-release", "status": "pending"}


@pytest.mark.asyncio
async def test_release_deployment_requires_approval_before_execute(tmp_path):
    approval_stub = ApprovalStub()
    agent = ReleaseDeploymentAgent(
        config={
            "approval_agent": approval_stub,
            "release_store_path": tmp_path / "releases.json",
            "deployment_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    release_response = await agent.process(
        {
            "action": "plan_release",
            "tenant_id": "tenant-rel",
            "release": {
                "name": "Release 1",
                "target_environment": "production",
                "planned_date": "2024-06-01",
                "requester": "release-manager",
            },
        }
    )
    assert release_response["approval_required"] is True
    assert agent.release_store.get("tenant-rel", release_response["release_id"])

    plan_response = await agent.process(
        {
            "action": "create_deployment_plan",
            "tenant_id": "tenant-rel",
            "release_id": release_response["release_id"],
            "deployment_plan": {"owner": "release-manager"},
        }
    )
    assert agent.deployment_plan_store.get("tenant-rel", plan_response["deployment_plan_id"])

    execute_response = await agent.process(
        {
            "action": "execute_deployment",
            "tenant_id": "tenant-rel",
            "deployment_plan_id": plan_response["deployment_plan_id"],
        }
    )
    assert execute_response["status"] == "Pending Approval"
    assert approval_stub.requests


@pytest.mark.asyncio
async def test_release_deployment_calendar_success(tmp_path):
    agent = ReleaseDeploymentAgent(
        config={
            "release_store_path": tmp_path / "releases.json",
            "deployment_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_release_calendar", "tenant_id": "tenant-rel"})

    assert "releases" in response


@pytest.mark.asyncio
async def test_release_deployment_validation_rejects_invalid_action(tmp_path):
    agent = ReleaseDeploymentAgent(config={"release_store_path": tmp_path / "releases.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_release_deployment_validation_rejects_missing_fields(tmp_path):
    agent = ReleaseDeploymentAgent(config={"release_store_path": tmp_path / "releases.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "plan_release", "release": {"name": "X"}})

    assert valid is False

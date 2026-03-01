import importlib.util
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "change-control-agent"
    / "src"
    / "change_configuration_agent.py"
)
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
spec = importlib.util.spec_from_file_location("change_configuration_agent", MODULE_PATH)
change_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(change_module)

ChangeConfigurationAgent = change_module.ChangeConfigurationAgent
ChangeImpactModel = change_module.ChangeImpactModel
ImpactTrainingSample = change_module.ImpactTrainingSample
RepositoryIntegrationService = change_module.RepositoryIntegrationService
RepositoryReference = change_module.RepositoryReference


def test_repository_integration_returns_unauthenticated_without_tokens() -> None:
    logger = logging.getLogger("repo-test")
    service = RepositoryIntegrationService(logger)
    reference = RepositoryReference(provider="github", repo="octo/org")

    response = service.list_pull_requests(reference)

    assert response.status == "unauthenticated"

    diff_response = service.fetch_pull_request_diff(
        RepositoryReference(provider="github", repo="octo/org", pull_request_id="1")
    )
    assert diff_response["status"] == "unauthenticated"


def test_change_impact_model_trains_with_samples() -> None:
    model = ChangeImpactModel()
    samples = [
        ImpactTrainingSample(2.0, 0.1, 3, "medium", 0.85),
        ImpactTrainingSample(4.0, 0.3, 8, "high", 0.6),
        ImpactTrainingSample(1.0, 0.05, 1, "low", 0.92),
    ]

    model.train(samples)

    prediction = model.predict(
        {
            "complexity": 2.5,
            "historical_failure_rate": 0.2,
            "affected_services": 4,
            "risk_category": "medium",
        }
    )
    assert prediction["model_trained"] is True
    assert 0.05 <= prediction["success_probability"] <= 0.95


@pytest.mark.anyio
async def test_compliance_impact_assessment() -> None:
    agent = ChangeConfigurationAgent(config={})
    change = {
        "compliance_scope": ["sox", "gdpr"],
        "regulatory_flags": ["pii"],
    }

    compliance = await agent._assess_compliance_impact(change)

    assert compliance["compliance_review_required"] is True
    assert compliance["compliance_risk_score"] > 0


@pytest.mark.anyio
async def test_change_category_and_trend_metrics() -> None:
    agent = ChangeConfigurationAgent(config={})
    now = datetime.utcnow()
    agent.change_requests = {
        "change-1": {
            "change_id": "change-1",
            "type": "normal",
            "classification": {"category": "routine"},
            "priority": "low",
            "status": "Implemented",
            "created_at": (now - timedelta(days=10)).isoformat(),
            "approval_date": (now - timedelta(days=9)).isoformat(),
        },
        "change-2": {
            "change_id": "change-2",
            "type": "emergency",
            "classification": {"category": "urgent"},
            "priority": "critical",
            "status": "Approved",
            "created_at": (now - timedelta(days=40)).isoformat(),
            "approval_date": (now - timedelta(days=39)).isoformat(),
        },
    }

    metrics = await agent._get_change_metrics({})

    assert metrics["change_type_counts"]["normal"] == 1
    assert metrics["change_category_counts"]["urgent"] == 1
    assert metrics["monthly_trends"]


@pytest.mark.anyio
async def test_automated_tests_skipped_without_endpoint() -> None:
    agent = ChangeConfigurationAgent(config={})
    change = {"change_id": "CHG-1", "title": "Change"}

    result = await agent._run_automated_tests(change, {})

    assert result["status"] == "skipped"

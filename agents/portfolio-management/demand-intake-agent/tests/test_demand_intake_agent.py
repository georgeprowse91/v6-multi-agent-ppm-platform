from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[
    3
]  # agents/portfolio-management/demand-intake-agent/tests/ -> up 3 = repo root
SRC_DIR = TESTS_DIR.parent / "src"
sys.path.extend(
    [
        str(SRC_DIR),
        str(REPO_ROOT),
        str(REPO_ROOT / "packages"),
        str(REPO_ROOT / "agents" / "runtime"),
    ]
)

from demand_intake_agent import DemandIntakeAgent
from demand_intake_utils import combine_demand_text, cosine_similarity, generate_demand_id, tokenize

# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------


def test_combine_demand_text_concatenates_fields() -> None:
    """combine_demand_text should join title, description, and business_objective."""
    data = {
        "title": "New Analytics Platform",
        "description": "Build a real-time analytics platform",
        "business_objective": "Improve data-driven decisions",
    }
    result = combine_demand_text(data)
    assert "new analytics platform" in result
    assert "real-time analytics platform" in result
    assert "improve data-driven decisions" in result


def test_combine_demand_text_handles_missing_fields() -> None:
    """combine_demand_text should tolerate missing keys."""
    result = combine_demand_text({"title": "Only Title"})
    assert result == "only title"


def test_tokenize_removes_stopwords() -> None:
    """tokenize should strip common stopwords and return meaningful tokens."""
    tokens = tokenize("the quick brown fox and the lazy dog")
    assert "the" not in tokens
    assert "and" not in tokens
    assert "quick" in tokens
    assert "fox" in tokens


def test_tokenize_lowercases_and_splits() -> None:
    """tokenize should lowercase input and split on non-alphanumeric boundaries."""
    tokens = tokenize("Finance SYSTEM upgrade")
    assert "finance" in tokens
    assert "system" in tokens
    assert "upgrade" in tokens


def test_cosine_similarity_identical_vectors() -> None:
    """Cosine similarity of a vector with itself should be 1.0."""
    vec = [1.0, 2.0, 3.0]
    assert cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors() -> None:
    """Cosine similarity of orthogonal vectors should be 0.0."""
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector() -> None:
    """Cosine similarity with a zero vector should return 0.0 without error."""
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


def test_generate_demand_id_has_dem_prefix() -> None:
    """generate_demand_id should produce IDs starting with 'DEM-'."""
    demand_id = generate_demand_id()
    assert demand_id.startswith("DEM-")


def test_generate_demand_id_is_unique() -> None:
    """Two successive calls to generate_demand_id should produce different IDs."""
    id1 = generate_demand_id()
    id2 = generate_demand_id()
    assert id1 != id2


# ---------------------------------------------------------------------------
# Agent-level tests (using lightweight mocks)
# ---------------------------------------------------------------------------


class _MockEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, object]] = []

    async def publish(self, topic: str, payload: object) -> None:
        self.published.append((topic, payload))


class _MockNotificationService:
    def __init__(self, _event_bus: object) -> None:
        self.sent: list[object] = []

    async def send(self, notification: object) -> None:
        self.sent.append(notification)


class _MockVectorIndex:
    def __init__(self, _embedding_service: object, *, index_name: str = "") -> None:
        self._docs: dict[str, object] = {}

    def add(self, doc_id: str, text: str, metadata: object) -> None:
        self._docs[doc_id] = metadata

    def search(self, query: str, top_k: int = 10) -> list[object]:
        return []


class _MockEmbeddingService:
    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions


class _MockClassifier:
    def __init__(self, labels: list[str]) -> None:
        self.labels = labels

    def fit(self, samples: list[object]) -> None:
        pass

    def predict(self, text: str) -> tuple[str, dict[str, float]]:
        return self.labels[0], {label: 0.25 for label in self.labels}


class _MockTenantStateStore:
    def __init__(self, path: object) -> None:
        self._store: dict[str, dict[str, object]] = {}

    def list(self, tenant_id: str) -> list[object]:
        return list(self._store.get(tenant_id, {}).values())

    def upsert(self, tenant_id: str, item_id: str, data: object) -> None:
        self._store.setdefault(tenant_id, {})[item_id] = data


def _build_agent() -> DemandIntakeAgent:
    """Build a DemandIntakeAgent with all external services mocked out."""
    event_bus = _MockEventBus()
    agent = DemandIntakeAgent(
        config={
            "event_bus": event_bus,
            "demand_store_path": ":memory:",
        }
    )
    agent.event_bus = event_bus
    agent.notification_service = _MockNotificationService(event_bus)
    agent.vector_index = _MockVectorIndex(None, index_name="demand_intake")
    agent.embedding_service = _MockEmbeddingService()
    agent.classifier = _MockClassifier(labels=["project", "change_request", "issue", "idea"])
    agent.classifier.fit([])
    agent.demand_store = _MockTenantStateStore(None)
    return agent


@pytest.mark.anyio
async def test_submit_request_returns_demand_id() -> None:
    """submit_request action should return a valid demand_id."""
    agent = _build_agent()
    result = await agent.process(
        {
            "action": "submit_request",
            "request": {
                "title": "Finance System Upgrade",
                "description": "Upgrade the legacy finance system",
                "business_objective": "Reduce operational costs",
                "requester": "alice@example.com",
            },
            "context": {"tenant_id": "tenant-1", "correlation_id": "corr-123"},
        }
    )
    assert "demand_id" in result
    assert result["demand_id"].startswith("DEM-")
    assert result["status"] == "Received"
    assert "category" in result


@pytest.mark.anyio
async def test_check_duplicates_empty_store() -> None:
    """check_duplicates with an empty store should return no duplicates."""
    agent = _build_agent()
    result = await agent.process(
        {
            "action": "check_duplicates",
            "request": {
                "title": "New Project",
                "description": "A brand new project",
                "business_objective": "Growth",
            },
            "context": {"tenant_id": "tenant-empty"},
        }
    )
    assert result["duplicates_found"] is False
    assert result["similar_requests"] == []


@pytest.mark.anyio
async def test_get_pipeline_returns_stats() -> None:
    """get_pipeline should return total_requests, by_status, and by_category."""
    agent = _build_agent()
    result = await agent.process(
        {
            "action": "get_pipeline",
            "filters": {},
            "context": {"tenant_id": "tenant-1"},
        }
    )
    assert "total_requests" in result
    assert "by_status" in result
    assert "by_category" in result
    assert isinstance(result["items"], list)


@pytest.mark.anyio
async def test_validate_input_rejects_missing_mandatory_fields() -> None:
    """validate_input should return False when mandatory fields are missing."""
    agent = _build_agent()
    # Patch schema/rule validation to pass — we test only mandatory_fields check
    import unittest.mock as mock

    with (
        mock.patch("demand_intake_agent.validate_against_schema", return_value=[]),
        mock.patch("demand_intake_agent.apply_rule_set") as mock_rule,
    ):
        mock_rule_result = mock.MagicMock()
        mock_rule_result.is_valid = True
        mock_rule.return_value = mock_rule_result

        valid = await agent.validate_input(
            {
                "action": "submit_request",
                "request": {
                    "title": "Missing description and objective",
                    # description and business_objective are missing
                },
            }
        )
    assert valid is False


@pytest.mark.anyio
async def test_validate_input_accepts_valid_request() -> None:
    """validate_input should return True for a well-formed request."""
    agent = _build_agent()
    import unittest.mock as mock

    with (
        mock.patch("demand_intake_agent.validate_against_schema", return_value=[]),
        mock.patch("demand_intake_agent.apply_rule_set") as mock_rule,
    ):
        mock_rule_result = mock.MagicMock()
        mock_rule_result.is_valid = True
        mock_rule.return_value = mock_rule_result

        valid = await agent.validate_input(
            {
                "action": "submit_request",
                "request": {
                    "title": "Finance Upgrade",
                    "description": "Upgrade legacy finance",
                    "business_objective": "Cut costs",
                },
            }
        )
    assert valid is True


def test_get_capabilities_returns_expected() -> None:
    """get_capabilities should return the documented list of capabilities."""
    agent = _build_agent()
    capabilities = agent.get_capabilities()
    assert "multi_channel_intake" in capabilities
    assert "automatic_categorization" in capabilities
    assert "duplicate_detection" in capabilities
    assert "preliminary_triage" in capabilities
    assert "pipeline_visualization" in capabilities
    assert "requester_communication" in capabilities

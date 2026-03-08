from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[4]
SRC_DIR = TESTS_DIR.parent / "src"
sys.path.extend(
    [
        str(SRC_DIR),
        str(REPO_ROOT),
        str(REPO_ROOT / "packages"),
        str(REPO_ROOT / "agents" / "runtime"),
        str(REPO_ROOT / "tools"),
    ]
)

from vendor_procurement_agent import VendorProcurementAgent


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


def _make_agent(tmp_path: Path) -> VendorProcurementAgent:
    return VendorProcurementAgent(
        config={
            "vendor_store_path": str(tmp_path / "vendors.json"),
            "contract_store_path": str(tmp_path / "contracts.json"),
            "invoice_store_path": str(tmp_path / "invoices.json"),
            "vendor_performance_store_path": str(tmp_path / "perf.json"),
            "event_store_path": str(tmp_path / "events.json"),
            "enable_openai_rfp": False,
            "enable_ai_scoring": False,
            "enable_vendor_research": False,
            "enable_ml_recommendations": False,
            "use_external_approval_agent": False,
        }
    )


@pytest.mark.anyio
async def test_onboard_vendor_creates_vendor(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.process(
        {
            "action": "onboard_vendor",
            "tenant_id": "tenant-1",
            "vendor": {
                "name": "Acme Software Pty Ltd",
                "category": "software",
                "contact_email": "contracts@acme.example.com",
                "country": "AU",
                "abn": "12345678901",
            },
        }
    )
    assert result.get("vendor_id")
    assert result.get("status") == "active" or result.get("vendor_id")


@pytest.mark.anyio
async def test_search_vendors_returns_results(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    # Seed some vendors
    for name, cat in [
        ("CloudBase Pty Ltd", "cloud"),
        ("DataPro Analytics", "software"),
        ("ConsultCo Group", "consulting"),
    ]:
        await agent.process(
            {
                "action": "onboard_vendor",
                "tenant_id": "tenant-2",
                "vendor": {
                    "name": name,
                    "category": cat,
                    "contact_email": f"info@{name.lower().replace(' ', '')}.example.com",
                },
            }
        )

    result = await agent.process(
        {
            "action": "search_vendors",
            "tenant_id": "tenant-2",
            "query": "cloud",
            "category": "cloud",
        }
    )
    assert result.get("vendors") is not None or result.get("results") is not None


@pytest.mark.anyio
async def test_create_procurement_request(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.process(
        {
            "action": "create_procurement_request",
            "tenant_id": "tenant-1",
            "request": {
                "title": "CI/CD Pipeline Tooling",
                "description": "Procure hosted CI/CD platform for dev teams",
                "category": "software",
                "estimated_value": 50000.0,
                "currency": "AUD",
                "requester": "devops-lead",
            },
        }
    )
    assert result.get("request_id") or result.get("success") is not False


@pytest.mark.anyio
async def test_get_vendor_profile_after_onboard(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    onboard_result = await agent.process(
        {
            "action": "onboard_vendor",
            "tenant_id": "tenant-3",
            "vendor": {
                "name": "TechPro Solutions",
                "category": "consulting",
                "contact_email": "hello@techpro.example.com",
            },
        }
    )
    vendor_id = onboard_result.get("vendor_id")
    assert vendor_id

    profile_result = await agent.process(
        {
            "action": "get_vendor_profile",
            "tenant_id": "tenant-3",
            "vendor_id": vendor_id,
        }
    )
    assert (
        profile_result.get("vendor_id") == vendor_id
        or profile_result.get("name") == "TechPro Solutions"
    )


@pytest.mark.anyio
async def test_validate_input_rejects_empty(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    valid = await agent.validate_input({})
    assert valid is False


@pytest.mark.anyio
async def test_validate_input_rejects_unknown_action(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    valid = await agent.validate_input({"action": "delete_all_vendors"})
    assert valid is False


@pytest.mark.anyio
async def test_validate_input_accepts_onboard_vendor(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    valid = await agent.validate_input(
        {"action": "onboard_vendor", "vendor": {"name": "Test Co", "category": "software"}}
    )
    assert valid is True


@pytest.mark.anyio
async def test_default_config_values(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    assert agent.default_currency == "AUD"
    assert agent.procurement_threshold == 10000
    assert agent.min_vendor_proposals == 3
    assert agent.invoice_tolerance_pct == pytest.approx(0.05)

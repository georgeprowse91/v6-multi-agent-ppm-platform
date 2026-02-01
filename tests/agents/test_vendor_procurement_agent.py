import pytest
import vendor_procurement_agent as vendor_procurement_module
from vendor_procurement_agent import VendorProcurementAgent


class ApprovalStub:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"approval_id": "appr-1", "status": "pending"}


class TaskClientStub:
    def __init__(self) -> None:
        self.tasks: list[dict] = []

    async def create_task(
        self, *, tenant_id: str, instance_id: str, task_type: str, payload: dict
    ) -> dict:
        task = {
            "tenant_id": tenant_id,
            "instance_id": instance_id,
            "task_type": task_type,
            "payload": payload,
        }
        self.tasks.append(task)
        return {"task_id": f"task-{len(self.tasks)}", "status": "queued"}


class CommunicationsStub:
    def __init__(self) -> None:
        self.notifications: list[dict] = []

    async def notify(
        self,
        *,
        tenant_id: str,
        subject: str,
        body: str,
        stakeholders: list[str] | None = None,
        channel: str = "email",
        metadata: dict | None = None,
    ) -> dict:
        payload = {
            "tenant_id": tenant_id,
            "subject": subject,
            "body": body,
            "stakeholders": stakeholders or [],
            "channel": channel,
            "metadata": metadata or {},
        }
        self.notifications.append(payload)
        return {"status": "sent", "subject": subject}


@pytest.mark.asyncio
async def test_vendor_procurement_persists_and_requests_approval(tmp_path):
    approval_stub = ApprovalStub()
    agent = VendorProcurementAgent(
        config={
            "approval_agent": approval_stub,
            "vendor_store_path": tmp_path / "vendors.json",
            "contract_store_path": tmp_path / "contracts.json",
            "invoice_store_path": tmp_path / "invoices.json",
            "vendor_performance_store_path": tmp_path / "vendor_performance.json",
            "event_store_path": tmp_path / "events.json",
        }
    )
    await agent.initialize()

    vendor_response = await agent.process(
        {
            "action": "onboard_vendor",
            "tenant_id": "tenant-x",
            "vendor": {
                "legal_name": "Starlight Software",
                "contact_email": "vendor@example.com",
                "category": "software",
                "owner": "procurement-lead",
                "requester": "procurement-lead",
            },
        }
    )

    vendor_id = vendor_response["vendor_id"]
    assert agent.vendor_store.get("tenant-x", vendor_id)

    request_response = await agent.process(
        {
            "action": "create_procurement_request",
            "tenant_id": "tenant-x",
            "request": {
                "requester": "procurement-lead",
                "description": "Enterprise licenses",
                "estimated_cost": 20000,
            },
        }
    )
    assert request_response["approval_required"] is True
    assert approval_stub.requests

    contract_response = await agent.process(
        {
            "action": "create_contract",
            "tenant_id": "tenant-x",
            "contract": {
                "vendor_id": vendor_id,
                "project_id": "project-1",
                "value": 20000,
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        }
    )
    assert agent.contract_store.get("tenant-x", contract_response["contract_id"])

    invoice_response = await agent.process(
        {
            "action": "submit_invoice",
            "tenant_id": "tenant-x",
            "invoice": {
                "invoice_number": "INV-001",
                "vendor_id": vendor_id,
                "po_number": "PO-1",
                "invoice_date": "2024-01-10",
                "total_amount": 20000,
            },
        }
    )
    assert agent.invoice_store.get("tenant-x", invoice_response["invoice_id"])
    events = agent.event_store.list("tenant-x")
    event_types = {event["event_type"] for event in events}
    assert "vendor.onboarded" in event_types
    assert "invoice.received" in event_types


@pytest.mark.asyncio
async def test_vendor_procurement_status_success(tmp_path):
    agent = VendorProcurementAgent(
        config={
            "vendor_store_path": tmp_path / "vendors.json",
            "contract_store_path": tmp_path / "contracts.json",
            "invoice_store_path": tmp_path / "invoices.json",
            "vendor_performance_store_path": tmp_path / "vendor_performance.json",
            "event_store_path": tmp_path / "events.json",
        }
    )
    await agent.initialize()

    request = await agent.process(
        {
            "action": "create_procurement_request",
            "tenant_id": "tenant-x",
            "request": {
                "requester": "procurement",
                "description": "Licenses",
                "estimated_cost": 1000,
            },
        }
    )

    response = await agent.process(
        {
            "action": "get_procurement_status",
            "tenant_id": "tenant-x",
            "request_id": request["request_id"],
        }
    )

    assert response["request_id"] == request["request_id"]


@pytest.mark.asyncio
async def test_vendor_procurement_validation_rejects_invalid_action(tmp_path):
    agent = VendorProcurementAgent(config={"vendor_store_path": tmp_path / "vendors.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_vendor_procurement_validation_rejects_missing_vendor_fields(tmp_path):
    agent = VendorProcurementAgent(config={"vendor_store_path": tmp_path / "vendors.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "onboard_vendor", "vendor": {"legal_name": "X"}})

    assert valid is False


@pytest.mark.asyncio
async def test_vendor_procurement_research_enriches_scorecard(tmp_path, monkeypatch):
    async def fake_search(_query: str, *, result_limit: int | None = None) -> list[str]:
        return ["Vendor health report (https://example.com/vendor)"]

    async def fake_summary(_snippets, **_kwargs):
        return "Positive financial outlook."

    async def fake_extract(self, _summary, _snippets, *, llm_client=None):
        return [
            {
                "category": "financial",
                "sentiment": "positive",
                "detail": "Strong balance sheet.",
                "source_url": "https://example.com/vendor",
            }
        ]

    monkeypatch.setattr(vendor_procurement_module, "search_web", fake_search)
    monkeypatch.setattr(vendor_procurement_module, "summarize_snippets", fake_summary)
    monkeypatch.setattr(VendorProcurementAgent, "_extract_vendor_insights", fake_extract)

    agent = VendorProcurementAgent(
        config={
            "enable_vendor_research": True,
            "vendor_store_path": tmp_path / "vendors.json",
            "contract_store_path": tmp_path / "contracts.json",
            "invoice_store_path": tmp_path / "invoices.json",
            "vendor_performance_store_path": tmp_path / "vendor_performance.json",
            "event_store_path": tmp_path / "events.json",
        }
    )
    await agent.initialize()

    vendor_response = await agent.process(
        {
            "action": "onboard_vendor",
            "tenant_id": "tenant-x",
            "vendor": {
                "legal_name": "Brightline Labs",
                "contact_email": "vendor@example.com",
                "category": "software",
                "owner": "procurement",
                "requester": "procurement",
            },
        }
    )

    scorecard = await agent.process(
        {
            "action": "get_vendor_scorecard",
            "tenant_id": "tenant-x",
            "vendor_id": vendor_response["vendor_id"],
        }
    )

    assert scorecard["external_research"]


@pytest.mark.asyncio
async def test_vendor_procurement_rfp_and_performance_updates(tmp_path):
    agent = VendorProcurementAgent(
        config={
            "vendor_store_path": tmp_path / "vendors.json",
            "contract_store_path": tmp_path / "contracts.json",
            "invoice_store_path": tmp_path / "invoices.json",
            "vendor_performance_store_path": tmp_path / "vendor_performance.json",
            "event_store_path": tmp_path / "events.json",
            "enable_openai_rfp": False,
            "enable_ai_scoring": False,
            "rfp_templates": {
                "software": {"template_id": "custom-soft", "sections": ["Overview", "Pricing"]},
            },
        }
    )
    await agent.initialize()

    vendor_response = await agent.process(
        {
            "action": "onboard_vendor",
            "tenant_id": "tenant-x",
            "vendor": {
                "legal_name": "Skyline Apps",
                "contact_email": "vendor@example.com",
                "category": "software",
                "owner": "procurement",
                "requester": "procurement",
            },
        }
    )

    request_response = await agent.process(
        {
            "action": "create_procurement_request",
            "tenant_id": "tenant-x",
            "request": {
                "requester": "procurement",
                "description": "New SaaS tools",
                "estimated_cost": 9000,
            },
        }
    )

    rfp_response = await agent.process(
        {
            "action": "generate_rfp",
            "tenant_id": "tenant-x",
            "request_id": request_response["request_id"],
            "rfp": {"template_id": "custom-soft", "requirements": ["SOC2", "SSO"]},
        }
    )

    assert rfp_response["rfp_id"] in agent.rfps
    assert "Template Sections" in agent.rfps[rfp_response["rfp_id"]]["content"]

    performance = await agent.process(
        {
            "action": "track_vendor_performance",
            "tenant_id": "tenant-x",
            "vendor_id": vendor_response["vendor_id"],
        }
    )

    stored = agent.vendor_performance_store.get("tenant-x", vendor_response["vendor_id"])
    assert stored
    assert performance["ml_analysis"]


@pytest.mark.asyncio
async def test_vendor_procurement_compliance_checks_use_risk_sources(tmp_path):
    agent = VendorProcurementAgent(
        config={
            "vendor_store_path": tmp_path / "vendors.json",
            "risk_config": {
                "mock_responses": {
                    "Risky Vendor": {
                        "sanctions_check": "Fail",
                        "anti_corruption_check": "Pass",
                        "credit_check": "Pass",
                        "watchlist_hits": ["Sanctioned entity list"],
                        "sources": [{"name": "mock-sanctions", "status": "Fail"}],
                    }
                }
            },
        }
    )
    await agent.initialize()

    checks = await agent._run_compliance_checks(
        {"legal_name": "Risky Vendor", "contact_email": "risk@example.com"}
    )

    assert checks["sanctions_check"] == "Fail"
    assert checks["watchlist_hits"]


@pytest.mark.asyncio
async def test_event_bus_publishes_and_dispatches_handlers():
    received: list[dict] = []

    async def handler(event: dict) -> None:
        received.append(event)

    event_bus = vendor_procurement_module.EventBusClient(config={"enabled": True})
    event_bus.register_handler("vendor.onboarded", handler)
    publisher = vendor_procurement_module.ProcurementEventPublisher(event_bus=event_bus)

    await publisher.publish({"event_id": "evt-1", "event_type": "vendor.onboarded"})

    assert received


@pytest.mark.asyncio
async def test_ml_recommendations_rank_vendors():
    ml_service = vendor_procurement_module.VendorMLService(
        config={
            "training_data": [
                {
                    "quality_rating": 90,
                    "on_time_delivery_rate": 95,
                    "compliance_rating": 98,
                    "risk_score": 90,
                    "dispute_count": 9,
                    "total_spend": 80,
                    "label": 1,
                },
                {
                    "quality_rating": 40,
                    "on_time_delivery_rate": 60,
                    "compliance_rating": 70,
                    "risk_score": 30,
                    "dispute_count": 2,
                    "total_spend": 10,
                    "label": 0,
                },
            ]
        }
    )
    await ml_service.train_models([])

    vendors = [
        {
            "vendor_id": "v-1",
            "category": "software",
            "status": "Approved",
            "risk_score": 40,
            "performance_metrics": {
                "quality_rating": 4.8,
                "on_time_delivery_rate": 98,
                "compliance_rating": 97,
            },
        },
        {
            "vendor_id": "v-2",
            "category": "software",
            "status": "Approved",
            "risk_score": 80,
            "performance_metrics": {
                "quality_rating": 3.0,
                "on_time_delivery_rate": 70,
                "compliance_rating": 80,
            },
        },
    ]

    recommendations = ml_service.recommend_vendors(vendors, "software", top_n=1)

    assert recommendations == ["v-1"]


def test_vendor_scoring_uses_weight_overrides():
    ml_service = vendor_procurement_module.VendorMLService(
        config={"scoring_weights": {"quality_rating": 0.5, "on_time_delivery_rate": 0.5}}
    )
    vendor = {
        "risk_score": 10,
        "performance_metrics": {"quality_rating": 4.0, "on_time_delivery_rate": 90},
    }
    score = ml_service.score_vendor(vendor)
    assert round(score, 1) == 85.0


@pytest.mark.asyncio
async def test_budget_checks_use_financial_client(tmp_path):
    agent = VendorProcurementAgent(
        config={
            "vendor_store_path": tmp_path / "vendors.json",
            "financial_config": {
                "budget_data": {"project-1": {"total": 5000, "committed": 1000}}
            },
        }
    )
    await agent.initialize()

    budget = await agent._check_budget_availability(
        {"project_id": "project-1", "estimated_cost": 6000}
    )

    assert budget["available"] is False


@pytest.mark.asyncio
async def test_vendor_procurement_blocks_and_mitigates_on_compliance_failure(tmp_path):
    task_stub = TaskClientStub()
    comms_stub = CommunicationsStub()
    agent = VendorProcurementAgent(
        config={
            "vendor_store_path": tmp_path / "vendors.json",
            "event_store_path": tmp_path / "events.json",
            "task_client": task_stub,
            "communications_client": comms_stub,
            "risk_config": {
                "mock_responses": {
                    "Risky Vendor": {
                        "sanctions_check": "Fail",
                        "anti_corruption_check": "Pass",
                        "credit_check": "Pass",
                        "watchlist_hits": ["Sanctioned entity list"],
                        "sources": [{"name": "mock-sanctions", "status": "Fail"}],
                    }
                }
            },
            "compliance_policy": {"block_on_fail": True, "flag_on_watchlist": True},
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "onboard_vendor",
            "tenant_id": "tenant-x",
            "vendor": {
                "legal_name": "Risky Vendor",
                "contact_email": "risk@example.com",
                "category": "software",
            },
        }
    )

    assert response["status"] == "blocked"
    assert response["compliance_status"] == "blocked"
    assert task_stub.tasks
    assert comms_stub.notifications
    events = agent.event_store.list("tenant-x")
    event_types = {event["event_type"] for event in events}
    assert "vendor.compliance_failed" in event_types
    assert "vendor.mitigation.initiated" in event_types


@pytest.mark.asyncio
async def test_vendor_procurement_updates_profile_and_queries(tmp_path):
    agent = VendorProcurementAgent(
        config={
            "vendor_store_path": tmp_path / "vendors.json",
        }
    )
    await agent.initialize()

    vendor_response = await agent.process(
        {
            "action": "onboard_vendor",
            "tenant_id": "tenant-x",
            "vendor": {
                "legal_name": "Evergreen Systems",
                "contact_email": "vendor@example.com",
                "category": "software",
            },
        }
    )

    update_response = await agent.process(
        {
            "action": "update_vendor_profile",
            "tenant_id": "tenant-x",
            "vendor_id": vendor_response["vendor_id"],
            "updates": {"status": "Approved", "risk_score": 20},
        }
    )

    assert update_response["status"] == "Approved"
    profile = await agent.process(
        {
            "action": "get_vendor_profile",
            "tenant_id": "tenant-x",
            "vendor_id": vendor_response["vendor_id"],
        }
    )
    assert profile["vendor"]["risk_score"] == 20


@pytest.mark.asyncio
async def test_vendor_procurement_mitigation_on_risk_event(tmp_path):
    task_stub = TaskClientStub()
    comms_stub = CommunicationsStub()
    agent = VendorProcurementAgent(
        config={
            "vendor_store_path": tmp_path / "vendors.json",
            "event_store_path": tmp_path / "events.json",
            "task_client": task_stub,
            "communications_client": comms_stub,
        }
    )
    await agent.initialize()

    vendor_response = await agent.process(
        {
            "action": "onboard_vendor",
            "tenant_id": "tenant-x",
            "vendor": {
                "legal_name": "Signal Metrics",
                "contact_email": "vendor@example.com",
                "category": "software",
            },
        }
    )

    await agent.event_bus.publish(
        {
            "event_id": "evt-risk-1",
            "event_type": "risk.alert",
            "tenant_id": "tenant-x",
            "correlation_id": "corr-1",
            "payload": {"vendor_id": vendor_response["vendor_id"], "risk_score": 92},
        }
    )

    vendor = agent.vendors[vendor_response["vendor_id"]]
    assert vendor["status"] == "flagged"
    assert task_stub.tasks
    assert comms_stub.notifications

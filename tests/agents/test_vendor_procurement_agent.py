import pytest

from vendor_procurement_agent import VendorProcurementAgent


class ApprovalStub:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"approval_id": "appr-1", "status": "pending"}


@pytest.mark.asyncio
async def test_vendor_procurement_persists_and_requests_approval(tmp_path):
    approval_stub = ApprovalStub()
    agent = VendorProcurementAgent(
        config={
            "approval_agent": approval_stub,
            "vendor_store_path": tmp_path / "vendors.json",
            "contract_store_path": tmp_path / "contracts.json",
            "invoice_store_path": tmp_path / "invoices.json",
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

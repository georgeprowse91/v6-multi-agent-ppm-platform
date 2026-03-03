"""Action handlers: submit_invoice, reconcile_invoice"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from vendor_utils import (
    generate_invoice_id,
    initiate_payment,
    publish_event,
    three_way_match,
)

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


async def handle_submit_invoice(
    agent: VendorProcurementAgent,
    invoice_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Submit vendor invoice.

    Returns invoice ID and receipt confirmation.
    """
    agent.logger.info("Submitting invoice: %s", invoice_data.get("invoice_number"))

    # Generate internal invoice ID
    invoice_id = await generate_invoice_id()

    # Create invoice record
    invoice = {
        "invoice_id": invoice_id,
        "vendor_invoice_number": invoice_data.get("invoice_number"),
        "vendor_id": invoice_data.get("vendor_id"),
        "po_number": invoice_data.get("po_number"),
        "invoice_date": invoice_data.get("invoice_date"),
        "due_date": invoice_data.get("due_date"),
        "line_items": invoice_data.get("line_items", []),
        "subtotal": invoice_data.get("subtotal"),
        "tax": invoice_data.get("tax"),
        "total_amount": invoice_data.get("total_amount"),
        "currency": invoice_data.get("currency", agent.default_currency),
        "payment_terms": invoice_data.get("payment_terms"),
        "attachments": invoice_data.get("attachments", []),
        "reconciliation_status": "Pending",
        "payment_status": "Unpaid",
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store invoice
    agent.invoices[invoice_id] = invoice
    agent.invoice_store.upsert(tenant_id, invoice_id, invoice)

    if agent.db_service:
        await agent.db_service.store("invoices", invoice_id, invoice)
    connector_results = agent.procurement_connector.record_invoice(invoice)
    await publish_event(
        agent,
        "invoice.received",
        payload={"invoice": invoice, "connector_results": connector_results},
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_id=invoice_id,
    )

    return {
        "invoice_id": invoice_id,
        "vendor_invoice_number": invoice["vendor_invoice_number"],
        "po_number": invoice["po_number"],
        "total_amount": invoice["total_amount"],
        "reconciliation_status": "Pending",
        "next_steps": "Invoice will be automatically reconciled against PO and receipts",
    }


async def handle_reconcile_invoice(
    agent: VendorProcurementAgent,
    invoice_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Reconcile invoice against PO and receipts (three-way matching).

    Returns reconciliation status and payment details.
    """
    agent.logger.info("Reconciling invoice: %s", invoice_id)

    invoice = agent.invoices.get(invoice_id)
    if not invoice:
        raise ValueError(f"Invoice not found: {invoice_id}")

    # Get associated PO
    po_number = invoice.get("po_number")
    purchase_order = agent.purchase_orders.get(po_number)
    if not purchase_order:
        raise ValueError(f"Purchase order not found: {po_number}")

    # Perform three-way matching
    matching_result = await three_way_match(agent, invoice, purchase_order)

    # Check for discrepancies
    discrepancies = matching_result.get("discrepancies", [])

    if not discrepancies:
        # No discrepancies - approve for payment
        invoice["reconciliation_status"] = "Matched"
        invoice["approved_for_payment"] = True
        invoice["approved_at"] = datetime.now(timezone.utc).isoformat()

        payment_status = await initiate_payment(agent, invoice)

        invoice["payment_status"] = payment_status.get("status", "Processing")
        invoice["payment_reference"] = payment_status.get("reference")
        invoice["payment_connector_results"] = payment_status.get("connector_results")

    else:
        # Discrepancies found - flag for review
        invoice["reconciliation_status"] = "Discrepancy"
        invoice["approved_for_payment"] = False
        invoice["discrepancies"] = discrepancies

    if agent.db_service:
        await agent.db_service.store("invoice_reconciliations", invoice_id, invoice)
    await publish_event(
        agent,
        "invoice.reconciled",
        payload={"invoice": invoice, "discrepancies": discrepancies},
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_id=invoice_id,
    )

    return {
        "invoice_id": invoice_id,
        "reconciliation_status": invoice["reconciliation_status"],
        "discrepancies": discrepancies,
        "approved_for_payment": invoice.get("approved_for_payment", False),
        "payment_status": invoice.get("payment_status"),
        "payment_reference": invoice.get("payment_reference"),
        "next_steps": (
            "Payment initiated" if not discrepancies else "Review and resolve discrepancies"
        ),
    }

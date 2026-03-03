"""
Action handler for governed connector write operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from data_sync_agent import DataSyncAgent


async def governed_connector_write(
    agent: DataSyncAgent,
    connector_id: str,
    resource_type: str,
    payloads: list[dict[str, Any]],
    *,
    approval_required: bool = False,
    approval_status: str | None = None,
    dry_run: bool = False,
    tenant_id: str = "",
) -> dict[str, Any]:
    """Write to an external connector through the governed connector runtime.

    This method enforces write-gating (connector status, approval,
    dry-run, audit logging, and idempotency) before delegating the
    actual write to the underlying connector instance.
    """
    connector = agent.connectors.get(connector_id) if hasattr(agent, "connectors") else None
    connector_status = "connected" if connector is not None else "not_configured"

    gate_result = agent.write_gate.check(
        connector_status=connector_status,
        approval_required=approval_required,
        approval_status=approval_status,
        dry_run_passed=True if not agent.write_gate.require_dry_run else (not dry_run),
        operation=f"sync:{resource_type}",
        entity_id=connector_id,
        agent_id=agent.agent_id,
        tenant_id=tenant_id,
    )

    if not gate_result.allowed:
        agent.logger.warning(
            "governed_write_blocked",
            extra={
                "connector_id": connector_id,
                "reason": gate_result.reason,
                "audit": gate_result.audit_entry,
            },
        )
        return {
            "status": "blocked",
            "reason": gate_result.reason,
            "idempotency_key": gate_result.idempotency_key,
        }

    if dry_run:
        agent.logger.info(
            "governed_write_dry_run",
            extra={"connector_id": connector_id, "resource": resource_type, "count": len(payloads)},
        )
        return {
            "status": "dry_run",
            "connector_id": connector_id,
            "resource_type": resource_type,
            "record_count": len(payloads),
            "idempotency_key": gate_result.idempotency_key,
        }

    try:
        result = connector.write(resource_type, payloads)
        agent.logger.info(
            "governed_write_success",
            extra={
                "connector_id": connector_id,
                "resource": resource_type,
                "count": len(payloads),
                "idempotency_key": gate_result.idempotency_key,
            },
        )
        return {
            "status": "written",
            "connector_id": connector_id,
            "resource_type": resource_type,
            "result": result,
            "idempotency_key": gate_result.idempotency_key,
        }
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.error(
            "governed_write_failed",
            extra={"connector_id": connector_id, "error": str(exc)},
        )
        return {
            "status": "failed",
            "connector_id": connector_id,
            "error": str(exc),
            "idempotency_key": gate_result.idempotency_key,
        }

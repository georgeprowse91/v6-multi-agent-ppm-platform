from __future__ import annotations

from datetime import datetime, timezone

from packages.contracts.src.events import (
    ApprovalCreatedEvent,
    ApprovalDecisionEvent,
    AuditEvent,
    BusinessCaseCreatedEvent,
    CharterCreatedEvent,
    DemandCreatedEvent,
    PortfolioPrioritizedEvent,
    ProgramCreatedEvent,
    ProjectTransitionedEvent,
    ScheduleBaselineLockedEvent,
    ScheduleDelayEvent,
    WbsCreatedEvent,
)


def _timestamp() -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_domain_events_validate() -> None:
    DemandCreatedEvent(
        event_name="demand.created",
        event_id="evt-12345678",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "demand_id": "demand-1",
            "source": "portal",
            "title": "New CRM",
            "submitted_by": "user-1",
            "submitted_at": _timestamp(),
        },
    )
    BusinessCaseCreatedEvent(
        event_name="business_case.created",
        event_id="evt-12345679",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "business_case_id": "bc-1",
            "demand_id": "demand-1",
            "project_name": "CRM Revamp",
            "created_at": _timestamp(),
            "owner": "owner-1",
        },
    )
    PortfolioPrioritizedEvent(
        event_name="portfolio.prioritized",
        event_id="evt-12345680",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "portfolio_id": "port-1",
            "cycle": "FY25",
            "prioritized_at": _timestamp(),
            "ranked_projects": ["proj-1", "proj-2"],
        },
    )
    ProgramCreatedEvent(
        event_name="program.created",
        event_id="evt-12345681",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "program_id": "prog-1",
            "name": "Payments",
            "portfolio_id": "port-1",
            "created_at": _timestamp(),
            "owner": "owner-2",
        },
    )
    CharterCreatedEvent(
        event_name="charter.created",
        event_id="evt-12345682",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "charter_id": "charter-1",
            "project_id": "proj-1",
            "created_at": _timestamp(),
            "owner": "owner-3",
        },
    )
    WbsCreatedEvent(
        event_name="wbs.created",
        event_id="evt-12345683",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "wbs_id": "wbs-1",
            "project_id": "proj-1",
            "created_at": _timestamp(),
            "baseline_date": _timestamp(),
        },
    )
    ProjectTransitionedEvent(
        event_name="project.transitioned",
        event_id="evt-12345684",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "project_id": "proj-1",
            "from_stage": "planning",
            "to_stage": "execution",
            "transitioned_at": _timestamp(),
            "actor_id": "user-1",
        },
    )
    ScheduleBaselineLockedEvent(
        event_name="schedule.baseline.locked",
        event_id="evt-12345685",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "project_id": "proj-1",
            "schedule_id": "sched-1",
            "locked_at": _timestamp(),
            "baseline_version": "v1",
        },
    )
    ScheduleDelayEvent(
        event_name="schedule.delay",
        event_id="evt-12345686",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "project_id": "proj-1",
            "schedule_id": "sched-1",
            "delay_days": 5,
            "reason": "Vendor delay",
            "detected_at": _timestamp(),
        },
    )
    ApprovalCreatedEvent(
        event_name="approval.created",
        event_id="evt-12345687",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "approval_id": "appr-1",
            "resource_type": "business_case",
            "resource_id": "bc-1",
            "stage": "initiation",
            "created_at": _timestamp(),
        },
    )
    ApprovalDecisionEvent(
        event_name="approval.decision",
        event_id="evt-12345688",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "approval_id": "appr-1",
            "decision": "approved",
            "decided_at": _timestamp(),
            "approver_id": "user-2",
            "comments": "Looks good",
        },
    )


def test_audit_event_validate() -> None:
    AuditEvent(
        event_name="audit.agent.policy",
        event_id="evt-12345689",
        timestamp=_timestamp(),
        tenant_id="tenant-a",
        payload={
            "id": "evt-12345689",
            "timestamp": _timestamp(),
            "tenant_id": "tenant-a",
            "action": "policy.evaluated",
            "outcome": "success",
            "classification": "internal",
            "actor": {"id": "test-agent-alpha", "type": "service", "roles": []},
            "resource": {"id": "policy-bundle", "type": "policy_bundle"},
            "metadata": {"decision": "allow"},
            "trace_id": "trace-1",
            "correlation_id": "corr-1",
        },
    )

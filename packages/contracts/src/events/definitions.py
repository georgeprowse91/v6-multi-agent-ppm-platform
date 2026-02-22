from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class EventEnvelope(BaseModel):
    event_name: str = Field(..., description="Event topic name")
    event_id: str = Field(..., min_length=8)
    timestamp: datetime
    tenant_id: str
    payload: Any
    correlation_id: str | None = None
    trace_id: str | None = None


class DemandCreatedPayload(BaseModel):
    demand_id: str
    source: str
    title: str
    submitted_by: str
    submitted_at: datetime


class DemandCreatedEvent(EventEnvelope):
    event_name: Literal["demand.created"]
    payload: DemandCreatedPayload


class BusinessCaseCreatedPayload(BaseModel):
    business_case_id: str
    demand_id: str
    project_name: str
    created_at: datetime
    owner: str


class BusinessCaseCreatedEvent(EventEnvelope):
    event_name: Literal["business_case.created"]
    payload: BusinessCaseCreatedPayload


class InvestmentRecommendationPayload(BaseModel):
    business_case_id: str
    recommendation: Literal["approve", "defer", "reject"]
    confidence_level: float
    generated_at: datetime
    owner: str


class InvestmentRecommendationEvent(EventEnvelope):
    event_name: Literal["investment.recommendation"]
    payload: InvestmentRecommendationPayload


class PortfolioPrioritizedPayload(BaseModel):
    portfolio_id: str
    cycle: str
    prioritized_at: datetime
    ranked_projects: list[str]


class PortfolioPrioritizedEvent(EventEnvelope):
    event_name: Literal["portfolio.prioritized"]
    payload: PortfolioPrioritizedPayload


class ProgramCreatedPayload(BaseModel):
    program_id: str
    name: str
    portfolio_id: str
    created_at: datetime
    owner: str


class ProgramCreatedEvent(EventEnvelope):
    event_name: Literal["program.created"]
    payload: ProgramCreatedPayload


class ProgramRoadmapUpdatedPayload(BaseModel):
    program_id: str
    roadmap_id: str
    updated_at: datetime
    milestone_count: int


class ProgramRoadmapUpdatedEvent(EventEnvelope):
    event_name: Literal["program.roadmap.updated"]
    payload: ProgramRoadmapUpdatedPayload


class CharterCreatedPayload(BaseModel):
    charter_id: str
    project_id: str
    created_at: datetime
    owner: str


class CharterCreatedEvent(EventEnvelope):
    event_name: Literal["charter.created"]
    payload: CharterCreatedPayload


class WbsCreatedPayload(BaseModel):
    wbs_id: str
    project_id: str
    created_at: datetime
    baseline_date: datetime | None = None


class WbsCreatedEvent(EventEnvelope):
    event_name: Literal["wbs.created"]
    payload: WbsCreatedPayload


class ScopeChangePayload(BaseModel):
    wbs_id: str
    project_id: str
    change_type: str = "update"
    updated_at: datetime | None = None
    actor_id: str | None = None


class ScopeChangeEvent(EventEnvelope):
    event_name: str  # flexible - "wbs.updated", "scope.changed", etc.
    payload: Any


class ProjectTransitionedPayload(BaseModel):
    project_id: str
    from_stage: str
    to_stage: str
    transitioned_at: datetime
    actor_id: str


class ProjectTransitionedEvent(EventEnvelope):
    event_name: Literal["project.transitioned"]
    payload: ProjectTransitionedPayload


class ProjectHealthUpdatedPayload(BaseModel):
    project_id: str
    health_data: dict


class ProjectHealthUpdatedEvent(EventEnvelope):
    event_name: Literal["project.health.updated"]
    payload: ProjectHealthUpdatedPayload


class ProjectHealthReportGeneratedPayload(BaseModel):
    report: dict


class ProjectHealthReportGeneratedEvent(EventEnvelope):
    event_name: Literal["project.health.report.generated"]
    payload: ProjectHealthReportGeneratedPayload


class ScheduleBaselineLockedPayload(BaseModel):
    project_id: str
    schedule_id: str
    locked_at: datetime
    baseline_version: str


class ScheduleBaselineLockedEvent(EventEnvelope):
    event_name: Literal["schedule.baseline.locked"]
    payload: ScheduleBaselineLockedPayload


class ScheduleDelayPayload(BaseModel):
    project_id: str
    schedule_id: str
    delay_days: int
    reason: str
    detected_at: datetime


class ScheduleDelayEvent(EventEnvelope):
    event_name: Literal["schedule.delay"]
    payload: ScheduleDelayPayload


class ResourceAllocationCreatedPayload(BaseModel):
    allocation_id: str
    resource_id: str
    project_id: str
    start_date: str
    end_date: str
    allocation_percentage: int


class ResourceAllocationCreatedEvent(EventEnvelope):
    event_name: Literal["resource.allocation.created"]
    payload: ResourceAllocationCreatedPayload


class ApprovalCreatedPayload(BaseModel):
    approval_id: str
    resource_type: str
    resource_id: str
    stage: str
    created_at: datetime


class ApprovalCreatedEvent(EventEnvelope):
    event_name: Literal["approval.created"]
    payload: ApprovalCreatedPayload


class HipaaAuditLogCreatedPayload(BaseModel):
    audit_log_id: str
    regulation: Literal["HIPAA"]
    resource_type: str
    resource_id: str
    action: str
    actor_id: str
    created_at: datetime
    details: dict | None = None


class HipaaAuditLogCreatedEvent(EventEnvelope):
    event_name: Literal["hipaa.audit_log.created"]
    payload: HipaaAuditLogCreatedPayload


class FdaCfrPart11AuditLogCreatedPayload(BaseModel):
    audit_log_id: str
    regulation: Literal["FDA_CFR_21_PART_11"]
    resource_type: str
    resource_id: str
    action: str
    actor_id: str
    created_at: datetime
    details: dict | None = None


class FdaCfrPart11AuditLogCreatedEvent(EventEnvelope):
    event_name: Literal["fda_cfr_21_part_11.audit_log.created"]
    payload: FdaCfrPart11AuditLogCreatedPayload


class ApprovalDecisionPayload(BaseModel):
    approval_id: str
    decision: Literal["approved", "rejected", "deferred"]
    decided_at: datetime
    approver_id: str
    comments: str | None = None


class ApprovalDecisionEvent(EventEnvelope):
    event_name: Literal["approval.decision"]
    payload: ApprovalDecisionPayload


class AuditActor(BaseModel):
    id: str
    type: Literal["user", "service", "system"]
    roles: list[str]


class AuditResource(BaseModel):
    id: str
    type: str
    attributes: dict | None = None


class AuditEventPayload(BaseModel):
    id: str
    timestamp: datetime
    tenant_id: str
    action: str
    outcome: Literal["success", "failure", "denied"]
    classification: Literal["public", "internal", "confidential", "restricted"]
    actor: AuditActor
    resource: AuditResource
    metadata: dict | None = None
    trace_id: str | None = None
    correlation_id: str | None = None


class AuditEvent(EventEnvelope):
    event_name: str
    payload: AuditEventPayload

    @field_validator("event_name")
    @classmethod
    def _validate_audit_event(cls, value: str) -> str:
        if not value.startswith("audit."):
            raise ValueError("audit events must start with 'audit.'")
        return value

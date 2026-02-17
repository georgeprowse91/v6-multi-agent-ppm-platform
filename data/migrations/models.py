from __future__ import annotations

from sqlalchemy import JSON, Column, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False)
    owner = Column(String(255), nullable=False)
    classification = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class Program(Base):
    __tablename__ = "programs"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    portfolio_id = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False)
    owner = Column(String(255), nullable=False)
    classification = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    program_id = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    owner = Column(String(255), nullable=False)
    classification = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    portfolio_id = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    currency = Column(String(8), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)
    owner = Column(String(255), nullable=False)
    classification = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class WorkItem(Base):
    __tablename__ = "work_items"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    assigned_to = Column(String(255), nullable=False)
    due_date = Column(Date, nullable=True)
    classification = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class Risk(Base):
    __tablename__ = "risks"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    impact = Column(String(32), nullable=False)
    likelihood = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    owner = Column(String(255), nullable=False)
    classification = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class Issue(Base):
    __tablename__ = "issues"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    project_id = Column(String(64), nullable=False)
    owner = Column(String(255), nullable=False)
    classification = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)
    owner = Column(String(255), nullable=False)
    classification = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    doc_type = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)
    classification = Column(String(32), nullable=False)
    owner = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    action = Column(String(128), nullable=False)
    outcome = Column(String(32), nullable=False)
    classification = Column(String(32), nullable=False)
    actor = Column(Text, nullable=False)
    resource = Column(Text, nullable=False)
    metadata_payload = Column("metadata", Text, nullable=True)
    trace_id = Column(String(64), nullable=True)
    correlation_id = Column(String(64), nullable=True)


class OrchestrationState(Base):
    __tablename__ = "orchestration_states"

    tenant_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), primary_key=True)
    status = Column(String(64), nullable=False)
    last_checkpoint = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class Demand(Base):
    __tablename__ = "demands"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    business_objective = Column(Text, nullable=False)
    requester = Column(String(255), nullable=True)
    business_unit = Column(String(255), nullable=True)
    urgency = Column(String(32), nullable=True)
    source = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class Resource(Base):
    __tablename__ = "resources"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False)
    metadata_payload = Column("metadata", JSON, nullable=True)


class Roi(Base):
    __tablename__ = "rois"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    roi = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    tenant_id = Column(String(64), primary_key=True)
    agents = Column(JSON, nullable=False)
    project_configs = Column(JSON, nullable=False)
    dev_users = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class SchemaRegistry(Base):
    __tablename__ = "schema_registry"

    name = Column(String(128), primary_key=True)
    version = Column(Integer, primary_key=True)
    schema = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)


class SchemaPromotion(Base):
    __tablename__ = "schema_promotions"

    name = Column(String(128), primary_key=True)
    version = Column(Integer, primary_key=True)
    environment = Column(String(32), primary_key=True)
    promoted_at = Column(DateTime, nullable=False)


class CanonicalEntity(Base):
    __tablename__ = "canonical_entities"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    schema_name = Column(String(128), nullable=False)
    schema_version = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

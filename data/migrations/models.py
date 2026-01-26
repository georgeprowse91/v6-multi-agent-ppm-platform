from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String, Text
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

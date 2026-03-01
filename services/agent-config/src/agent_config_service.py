"""
Agent Configuration Service

Provides CRUD operations for agent enablement and configuration parameters.
Uses a JSON-backed file store for persistence.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from sqlalchemy import Column, DateTime, ForeignKey, MetaData, String, Table, create_engine, func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import delete, insert, select

logger = logging.getLogger("agent-config")


class AgentCategory(StrEnum):
    """Agent categories for grouping."""

    CORE = "core"
    PORTFOLIO = "portfolio"
    DELIVERY = "delivery"
    OPERATIONS = "operations"
    PLATFORM = "platform"
    GOVERNANCE = "governance"


class UserRole(StrEnum):
    """User roles for permission checks."""

    PMO_ADMIN = "PMO_ADMIN"
    PM = "PM"
    TEAM_MEMBER = "TEAM_MEMBER"
    AUDITOR = "AUDITOR"
    COLLABORATOR = "COLLABORATOR"


RBAC_METADATA = MetaData()

RBAC_USERS_TABLE = Table(
    "rbac_users",
    RBAC_METADATA,
    Column("user_id", String(128), primary_key=True),
    Column("tenant_id", String(128), primary_key=True),
    Column("display_name", String(256)),
    Column("email", String(256)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
)

RBAC_ROLES_TABLE = Table(
    "rbac_roles",
    RBAC_METADATA,
    Column("role_id", String(128), primary_key=True),
    Column("description", String(256)),
)

RBAC_USER_ROLES_TABLE = Table(
    "rbac_user_roles",
    RBAC_METADATA,
    Column("user_id", String(128), primary_key=True),
    Column("tenant_id", String(128), primary_key=True),
    Column("role_id", String(128), ForeignKey("rbac_roles.role_id"), primary_key=True),
    Column("granted_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


def _to_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg"):
        return database_url.replace("postgresql+asyncpg", "postgresql", 1)
    if database_url.startswith("sqlite+aiosqlite"):
        return database_url.replace("sqlite+aiosqlite", "sqlite", 1)
    return database_url


class AgentConfigRBACStore:
    """RBAC data store for agent configuration permissions."""

    def __init__(self, database_url: str) -> None:
        self.database_url = _to_sync_database_url(database_url)
        self.engine: Engine = create_engine(self.database_url, pool_pre_ping=True)
        # In-memory fallback for environments where the DB stub is a no-op.
        self._mem_user_roles: dict[str, list[str]] = {}

    def initialize(self) -> None:
        RBAC_METADATA.create_all(self.engine)
        # create_all is a no-op in stub environments; fall back to raw SQLite DDL.
        if self.database_url.startswith("sqlite"):
            import sqlite3
            import re as _re
            m = _re.search(r"sqlite:///(.+)", self.database_url)
            if m:
                db_path = m.group(1)
                with sqlite3.connect(db_path) as conn:
                    conn.execute(
                        "CREATE TABLE IF NOT EXISTS rbac_roles ("
                        "  role_id TEXT PRIMARY KEY,"
                        "  description TEXT"
                        ")"
                    )
                    conn.execute(
                        "CREATE TABLE IF NOT EXISTS rbac_users ("
                        "  user_id TEXT PRIMARY KEY,"
                        "  tenant_id TEXT NOT NULL,"
                        "  display_name TEXT,"
                        "  email TEXT,"
                        "  created_at TEXT,"
                        "  updated_at TEXT"
                        ")"
                    )
                    conn.execute(
                        "CREATE TABLE IF NOT EXISTS rbac_user_roles ("
                        "  user_id TEXT NOT NULL,"
                        "  tenant_id TEXT NOT NULL,"
                        "  role_id TEXT NOT NULL REFERENCES rbac_roles(role_id),"
                        "  granted_at TEXT,"
                        "  PRIMARY KEY (user_id, tenant_id, role_id)"
                        ")"
                    )
                    conn.commit()

    def _sqlite_db_path(self) -> str | None:
        """Return the filesystem path if the database URL is SQLite, else None."""
        import re as _re
        m = _re.search(r"sqlite:///(.+)", self.database_url)
        return m.group(1) if m else None

    def _sync_sqlite(
        self,
        user_id: str,
        tenant_id: str,
        clean_roles: list[str],
        display_name: str | None,
        email: str | None,
    ) -> None:
        """Write RBAC data directly to the SQLite file (bypasses ORM stub)."""
        import sqlite3
        db_path = self._sqlite_db_path()
        if not db_path:
            return
        with sqlite3.connect(db_path) as conn:
            for role in clean_roles:
                conn.execute(
                    "INSERT OR IGNORE INTO rbac_roles (role_id, description) VALUES (?, ?)",
                    (role, None),
                )
            conn.execute(
                "INSERT OR REPLACE INTO rbac_users (user_id, tenant_id, display_name, email) "
                "VALUES (?, ?, ?, ?)",
                (user_id, tenant_id, display_name, email),
            )
            conn.execute(
                "DELETE FROM rbac_user_roles WHERE user_id = ? AND tenant_id = ?",
                (user_id, tenant_id),
            )
            for role in clean_roles:
                conn.execute(
                    "INSERT INTO rbac_user_roles (user_id, tenant_id, role_id) VALUES (?, ?, ?)",
                    (user_id, tenant_id, role),
                )
            conn.commit()

    def sync_user_roles(
        self,
        *,
        user_id: str,
        tenant_id: str,
        roles: list[str],
        display_name: str | None = None,
        email: str | None = None,
    ) -> None:
        clean_roles = sorted({role for role in roles if role})
        try:
            with self.engine.begin() as connection:
                existing = connection.execute(
                    select(RBAC_USERS_TABLE.c.user_id).where(
                        RBAC_USERS_TABLE.c.user_id == user_id,
                        RBAC_USERS_TABLE.c.tenant_id == tenant_id,
                    )
                ).first()
                if existing:
                    connection.execute(
                        RBAC_USERS_TABLE.update()
                        .where(
                            RBAC_USERS_TABLE.c.user_id == user_id,
                            RBAC_USERS_TABLE.c.tenant_id == tenant_id,
                        )
                        .values(display_name=display_name, email=email)
                    )
                else:
                    connection.execute(
                        RBAC_USERS_TABLE.insert().values(
                            user_id=user_id,
                            tenant_id=tenant_id,
                            display_name=display_name,
                            email=email,
                        )
                    )

                if clean_roles:
                    existing_roles = (
                        connection.execute(
                            select(RBAC_ROLES_TABLE.c.role_id).where(
                                RBAC_ROLES_TABLE.c.role_id.in_(clean_roles)
                            )
                        )
                        .scalars()
                        .all()
                    )
                    for role in clean_roles:
                        if role not in existing_roles:
                            connection.execute(
                                RBAC_ROLES_TABLE.insert().values(role_id=role, description=None)
                            )

                connection.execute(
                    delete(RBAC_USER_ROLES_TABLE).where(
                        RBAC_USER_ROLES_TABLE.c.user_id == user_id,
                        RBAC_USER_ROLES_TABLE.c.tenant_id == tenant_id,
                    )
                )
                for role in clean_roles:
                    connection.execute(
                        insert(RBAC_USER_ROLES_TABLE).values(
                            user_id=user_id, tenant_id=tenant_id, role_id=role
                        )
                    )
        except SQLAlchemyError as exc:
            logger.exception("rbac_sync_failed", extra={"user_id": user_id, "tenant_id": tenant_id})
            raise RuntimeError("Failed to sync RBAC roles") from exc
        # Update in-memory fallback so reads work in stub environments
        self._mem_user_roles[f"{user_id}:{tenant_id}"] = clean_roles
        # Also write directly to SQLite when engine is a stub
        if self._sqlite_db_path():
            self._sync_sqlite(user_id, tenant_id, clean_roles, display_name, email)

    def get_user_roles(self, user_id: str, tenant_id: str) -> list[str]:
        with self.engine.begin() as connection:
            result = connection.execute(
                select(RBAC_USER_ROLES_TABLE.c.role_id).where(
                    RBAC_USER_ROLES_TABLE.c.user_id == user_id,
                    RBAC_USER_ROLES_TABLE.c.tenant_id == tenant_id,
                )
            )
            rows = result.fetchall()
        if rows:
            return [row.role_id for row in rows]
        return list(self._mem_user_roles.get(f"{user_id}:{tenant_id}", []))

    def can_user_configure_agents(self, user_id: str, tenant_id: str) -> bool:
        roles = self.get_user_roles(user_id, tenant_id)
        return any(role in {UserRole.PMO_ADMIN.value, UserRole.PM.value} for role in roles)


@dataclass
class AgentParameter:
    """A configurable parameter for an agent."""

    name: str
    display_name: str
    description: str
    param_type: str  # "string", "number", "boolean", "select", "multiselect"
    default_value: Any
    current_value: Any | None = None
    options: list[str] | None = None  # For select/multiselect types
    min_value: float | None = None  # For number type
    max_value: float | None = None  # For number type
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentParameter:
        return cls(**data)


@dataclass
class AgentConfig:
    """Configuration for a single agent."""

    catalog_id: str
    agent_id: str
    display_name: str
    description: str
    category: AgentCategory
    enabled: bool = True
    parameters: list[AgentParameter] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_id": self.catalog_id,
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "description": self.description,
            "category": (
                self.category.value if isinstance(self.category, AgentCategory) else self.category
            ),
            "enabled": self.enabled,
            "parameters": [p.to_dict() for p in self.parameters],
            "capabilities": self.capabilities,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentConfig:
        params = [AgentParameter.from_dict(p) for p in data.get("parameters", [])]
        category = data.get("category", AgentCategory.CORE)
        if isinstance(category, str):
            category = AgentCategory(category)
        return cls(
            catalog_id=data["catalog_id"],
            agent_id=data["agent_id"],
            display_name=data["display_name"],
            description=data.get("description", ""),
            category=category,
            enabled=data.get("enabled", True),
            parameters=params,
            capabilities=data.get("capabilities", []),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            updated_by=data.get("updated_by"),
        )


@dataclass
class ProjectAgentConfig:
    """Project-specific agent configuration (enablement + parameter overrides)."""

    project_id: str
    agent_id: str
    enabled: bool = True
    parameter_overrides: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectAgentConfig:
        return cls(**data)


class AgentConfigStore:
    """JSON-backed store for agent configurations."""

    def __init__(self, store_path: Path, rbac_database_url: str) -> None:
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._initialize_store()
        self.rbac_store = AgentConfigRBACStore(rbac_database_url)
        self.rbac_store.initialize()

    def _initialize_store(self) -> None:
        """Initialize store with default agent configurations."""
        initial_data = {
            "agents": self._get_default_agents(),
            "project_configs": {},
        }
        self._save(initial_data)

    def _get_default_agents(self) -> dict[str, Any]:
        """Return default agent configurations."""
        agents = {}

        # Core Agents
        agents["intent-router-agent"] = AgentConfig(
            catalog_id="intent-router-agent",
            agent_id="intent-router-agent",
            display_name="Intent Router",
            description="Routes user queries to appropriate specialized agents",
            category=AgentCategory.CORE,
            enabled=True,
            capabilities=["query_routing", "intent_classification"],
            parameters=[
                AgentParameter(
                    name="confidence_threshold",
                    display_name="Confidence Threshold",
                    description="Minimum confidence score for routing decisions",
                    param_type="number",
                    default_value=0.7,
                    min_value=0.0,
                    max_value=1.0,
                ),
            ],
        ).to_dict()

        agents["response-orchestration-agent"] = AgentConfig(
            catalog_id="response-orchestration-agent",
            agent_id="response-orchestration-agent",
            display_name="Response Orchestration",
            description="Orchestrates responses from multiple agents",
            category=AgentCategory.CORE,
            enabled=True,
            capabilities=["response_aggregation", "context_management"],
            parameters=[
                AgentParameter(
                    name="max_concurrency",
                    display_name="Max Concurrency",
                    description="Maximum number of concurrent agent calls",
                    param_type="number",
                    default_value=5,
                    min_value=1,
                    max_value=20,
                ),
                AgentParameter(
                    name="timeout_seconds",
                    display_name="Timeout (seconds)",
                    description="Timeout for agent responses",
                    param_type="number",
                    default_value=30,
                    min_value=5,
                    max_value=120,
                ),
            ],
        ).to_dict()

        # Governance Agents
        agents["approval-workflow-agent"] = AgentConfig(
            catalog_id="approval-workflow-agent",
            agent_id="approval-workflow-agent",
            display_name="Approval Workflow",
            description="Unified workflow and approval engine — orchestrates long-running workflows, approval chains, task inboxes, and process automation",
            category=AgentCategory.GOVERNANCE,
            enabled=True,
            capabilities=["approval_management", "gate_review", "escalation", "workflow_execution", "process_automation", "task_routing"],
        ).to_dict()

        # Portfolio Agents
        agents["demand-intake-agent"] = AgentConfig(
            catalog_id="demand-intake-agent",
            agent_id="demand-intake-agent",
            display_name="Demand Intake",
            description="Handles intake of new project demands and requests",
            category=AgentCategory.PORTFOLIO,
            enabled=True,
            capabilities=["demand_capture", "prioritization", "initial_assessment"],
        ).to_dict()

        agents["business-case-agent"] = AgentConfig(
            catalog_id="business-case-agent",
            agent_id="business-case-agent",
            display_name="Business Case & Investment",
            description="Analyzes business cases and investment decisions",
            category=AgentCategory.PORTFOLIO,
            enabled=True,
            capabilities=["roi_analysis", "benefit_tracking", "investment_modeling"],
        ).to_dict()

        agents["portfolio-optimisation-agent"] = AgentConfig(
            catalog_id="portfolio-optimisation-agent",
            agent_id="portfolio-optimisation-agent",
            display_name="Portfolio Strategy & Optimization",
            description="Optimizes portfolio mix and strategic alignment",
            category=AgentCategory.PORTFOLIO,
            enabled=True,
            capabilities=["portfolio_analysis", "resource_optimization", "strategic_alignment"],
        ).to_dict()

        # Delivery Agents
        agents["program-management-agent"] = AgentConfig(
            catalog_id="program-management-agent",
            agent_id="program-management-agent",
            display_name="Program Management",
            description="Manages programs and cross-project coordination",
            category=AgentCategory.DELIVERY,
            enabled=True,
            capabilities=["program_planning", "dependency_management", "benefit_realization"],
        ).to_dict()

        agents["scope-definition-agent"] = AgentConfig(
            catalog_id="scope-definition-agent",
            agent_id="scope-definition-agent",
            display_name="Project Definition & Scope",
            description="Defines project scope and deliverables",
            category=AgentCategory.DELIVERY,
            enabled=True,
            capabilities=["scope_definition", "wbs_creation", "deliverable_tracking"],
            parameters=[
                AgentParameter(
                    name="enable_external_research",
                    display_name="Enable External Scope Research",
                    description="Allow the agent to call external search APIs for scope refinement",
                    param_type="boolean",
                    default_value=False,
                ),
                AgentParameter(
                    name="search_result_limit",
                    display_name="External Search Result Limit",
                    description="Maximum number of external search snippets to use",
                    param_type="number",
                    default_value=5,
                    min_value=1,
                    max_value=10,
                ),
            ],
        ).to_dict()

        agents["lifecycle-governance-agent"] = AgentConfig(
            catalog_id="lifecycle-governance-agent",
            agent_id="lifecycle-governance-agent",
            display_name="Project Lifecycle & Governance",
            description="Manages project lifecycle and governance processes",
            category=AgentCategory.GOVERNANCE,
            enabled=True,
            capabilities=["lifecycle_management", "gate_reviews", "health_monitoring"],
        ).to_dict()

        # Schedule & Planning Agent - with detailed parameters
        agents["schedule-planning-agent"] = AgentConfig(
            catalog_id="schedule-planning-agent",
            agent_id="schedule-planning-agent",
            display_name="Schedule & Planning",
            description="Manages project schedules, timelines, and critical path analysis",
            category=AgentCategory.DELIVERY,
            enabled=True,
            capabilities=[
                "schedule_creation",
                "critical_path_analysis",
                "milestone_tracking",
                "dependency_management",
                "baseline_management",
            ],
            parameters=[
                AgentParameter(
                    name="default_task_duration",
                    display_name="Default Task Duration (days)",
                    description="Default duration for new tasks",
                    param_type="number",
                    default_value=5,
                    min_value=1,
                    max_value=90,
                ),
                AgentParameter(
                    name="critical_path_buffer",
                    display_name="Critical Path Buffer (%)",
                    description="Buffer percentage for critical path calculations",
                    param_type="number",
                    default_value=10,
                    min_value=0,
                    max_value=50,
                ),
                AgentParameter(
                    name="schedule_variance_threshold",
                    display_name="Schedule Variance Threshold (%)",
                    description="Threshold for flagging schedule variances",
                    param_type="number",
                    default_value=15,
                    min_value=5,
                    max_value=50,
                ),
                AgentParameter(
                    name="auto_recalculate_dependencies",
                    display_name="Auto-recalculate Dependencies",
                    description="Automatically recalculate dependent tasks when dates change",
                    param_type="boolean",
                    default_value=True,
                ),
                AgentParameter(
                    name="working_days_per_week",
                    display_name="Working Days Per Week",
                    description="Number of working days per week for scheduling",
                    param_type="select",
                    default_value="5",
                    options=["5", "6", "7"],
                ),
                AgentParameter(
                    name="enable_persistence",
                    display_name="Enable Schedule Persistence",
                    description="Persist schedules to SQL storage",
                    param_type="boolean",
                    default_value=True,
                ),
                AgentParameter(
                    name="enable_event_publishing",
                    display_name="Enable Event Publishing",
                    description="Publish schedule events to the event bus",
                    param_type="boolean",
                    default_value=True,
                ),
                AgentParameter(
                    name="enable_analytics",
                    display_name="Enable Analytics Metrics",
                    description="Record schedule metrics via analytics module",
                    param_type="boolean",
                    default_value=True,
                ),
                AgentParameter(
                    name="enable_azure_ml",
                    display_name="Enable Azure ML Duration Models",
                    description="Train and use Azure ML models for duration estimation",
                    param_type="boolean",
                    default_value=False,
                ),
                AgentParameter(
                    name="enable_databricks",
                    display_name="Enable Databricks Monte Carlo",
                    description="Use Databricks for Monte Carlo simulation",
                    param_type="boolean",
                    default_value=False,
                ),
                AgentParameter(
                    name="enable_dependency_ai",
                    display_name="Enable AI Dependency Suggestions",
                    description="Use AI heuristics to suggest task dependencies",
                    param_type="boolean",
                    default_value=True,
                ),
                AgentParameter(
                    name="enable_external_sync",
                    display_name="Enable External Tool Sync",
                    description="Sync schedules with external tools",
                    param_type="boolean",
                    default_value=False,
                ),
                AgentParameter(
                    name="enable_calendar_sync",
                    display_name="Enable Calendar Sync",
                    description="Sync milestones to Outlook/Google Calendar",
                    param_type="boolean",
                    default_value=False,
                ),
                AgentParameter(
                    name="enable_cache",
                    display_name="Enable Schedule Cache",
                    description="Cache schedules in Redis/in-memory",
                    param_type="boolean",
                    default_value=True,
                ),
                AgentParameter(
                    name="cache_ttl_seconds",
                    display_name="Cache TTL (seconds)",
                    description="Time to live for cached schedules",
                    param_type="number",
                    default_value=600,
                    min_value=60,
                    max_value=3600,
                ),
                AgentParameter(
                    name="enable_ms_project",
                    display_name="Enable Microsoft Project Sync",
                    description="Push/pull schedules with Microsoft Project",
                    param_type="boolean",
                    default_value=False,
                ),
                AgentParameter(
                    name="enable_jira",
                    display_name="Enable Jira Sync",
                    description="Push/pull schedules with Jira",
                    param_type="boolean",
                    default_value=False,
                ),
                AgentParameter(
                    name="enable_azure_devops",
                    display_name="Enable Azure DevOps Sync",
                    description="Push/pull schedules with Azure DevOps",
                    param_type="boolean",
                    default_value=False,
                ),
                AgentParameter(
                    name="enable_smartsheet",
                    display_name="Enable Smartsheet Sync",
                    description="Push/pull schedules with Smartsheet",
                    param_type="boolean",
                    default_value=False,
                ),
                AgentParameter(
                    name="enable_outlook",
                    display_name="Enable Outlook Calendar Sync",
                    description="Sync milestones to Outlook calendar",
                    param_type="boolean",
                    default_value=False,
                ),
                AgentParameter(
                    name="enable_google_calendar",
                    display_name="Enable Google Calendar Sync",
                    description="Sync milestones to Google Calendar",
                    param_type="boolean",
                    default_value=False,
                ),
            ],
        ).to_dict()

        agents["resource-management-agent"] = AgentConfig(
            catalog_id="resource-management-agent",
            agent_id="resource-management-agent",
            display_name="Resource & Capacity",
            description="Manages resource allocation and capacity planning",
            category=AgentCategory.DELIVERY,
            enabled=True,
            capabilities=["resource_allocation", "capacity_planning", "skill_matching"],
        ).to_dict()

        # Financial Management Agent - with detailed parameters
        agents["financial-management-agent"] = AgentConfig(
            catalog_id="financial-management-agent",
            agent_id="financial-management-agent",
            display_name="Financial Management",
            description="Manages project finances, budgets, forecasts, and cost tracking",
            category=AgentCategory.PORTFOLIO,
            enabled=True,
            capabilities=[
                "budget_management",
                "cost_tracking",
                "forecasting",
                "variance_analysis",
                "evm_metrics",
            ],
            parameters=[
                AgentParameter(
                    name="currency",
                    display_name="Default Currency",
                    description="Default currency for financial calculations",
                    param_type="select",
                    default_value="AUD",
                    options=["AUD", "EUR", "GBP", "NZD", "CAD", "JPY"],
                ),
                AgentParameter(
                    name="cost_variance_threshold",
                    display_name="Cost Variance Threshold (%)",
                    description="Threshold for flagging cost variances",
                    param_type="number",
                    default_value=10,
                    min_value=1,
                    max_value=50,
                ),
                AgentParameter(
                    name="forecast_method",
                    display_name="Forecast Method",
                    description="Method for calculating forecasts",
                    param_type="select",
                    default_value="evm",
                    options=["evm", "trend", "manual", "hybrid"],
                ),
                AgentParameter(
                    name="enable_evm",
                    display_name="Enable Earned Value Management",
                    description="Calculate EVM metrics (CPI, SPI, EAC, etc.)",
                    param_type="boolean",
                    default_value=True,
                ),
                AgentParameter(
                    name="budget_contingency_percent",
                    display_name="Budget Contingency (%)",
                    description="Default contingency percentage for budgets",
                    param_type="number",
                    default_value=15,
                    min_value=0,
                    max_value=50,
                ),
                AgentParameter(
                    name="fiscal_year_start_month",
                    display_name="Fiscal Year Start Month",
                    description="Month when fiscal year begins",
                    param_type="select",
                    default_value="1",
                    options=["1", "4", "7", "10"],
                ),
            ],
        ).to_dict()

        # Operations Agents
        agents["vendor-procurement-agent"] = AgentConfig(
            catalog_id="vendor-procurement-agent",
            agent_id="vendor-procurement-agent",
            display_name="Vendor & Procurement",
            description="Manages vendor relationships and procurement processes",
            category=AgentCategory.OPERATIONS,
            enabled=True,
            capabilities=["vendor_management", "contract_tracking", "procurement"],
            parameters=[
                AgentParameter(
                    name="default_currency",
                    display_name="Default Currency",
                    description="Currency used for procurement transactions",
                    param_type="string",
                    default_value="AUD",
                ),
                AgentParameter(
                    name="procurement_threshold",
                    display_name="Procurement Threshold",
                    description="Spend threshold that triggers approvals",
                    param_type="number",
                    default_value=10000,
                    min_value=0,
                    max_value=1000000,
                ),
                AgentParameter(
                    name="min_vendor_proposals",
                    display_name="Minimum Vendor Proposals",
                    description="Minimum number of vendor proposals to collect",
                    param_type="number",
                    default_value=3,
                    min_value=1,
                    max_value=10,
                ),
                AgentParameter(
                    name="invoice_tolerance_pct",
                    display_name="Invoice Tolerance (%)",
                    description="Allowed variance for invoice reconciliation",
                    param_type="number",
                    default_value=0.05,
                    min_value=0,
                    max_value=0.5,
                ),
                AgentParameter(
                    name="vendor_categories",
                    display_name="Vendor Categories",
                    description="Default vendor categories for onboarding",
                    param_type="multiselect",
                    default_value=[
                        "software",
                        "hardware",
                        "consulting",
                        "materials",
                        "services",
                        "cloud",
                    ],
                    options=[
                        "software",
                        "hardware",
                        "consulting",
                        "materials",
                        "services",
                        "cloud",
                    ],
                ),
            ],
        ).to_dict()

        agents["quality-management-agent"] = AgentConfig(
            catalog_id="quality-management-agent",
            agent_id="quality-management-agent",
            display_name="Quality Management",
            description="Manages quality assurance and quality control processes",
            category=AgentCategory.OPERATIONS,
            enabled=True,
            capabilities=["quality_planning", "defect_tracking", "quality_metrics"],
            parameters=[
                AgentParameter(
                    name="defect_severity_levels",
                    display_name="Defect Severity Levels",
                    description="Supported defect severity options",
                    param_type="multiselect",
                    default_value=["critical", "high", "medium", "low"],
                    options=["critical", "high", "medium", "low"],
                ),
                AgentParameter(
                    name="quality_standards",
                    display_name="Quality Standards",
                    description="Quality standards used for audits",
                    param_type="multiselect",
                    default_value=["ISO 9001", "CMMI", "IEEE 829"],
                    options=["ISO 9001", "CMMI", "IEEE 829"],
                ),
                AgentParameter(
                    name="min_test_coverage",
                    display_name="Minimum Test Coverage",
                    description="Minimum acceptable test coverage",
                    param_type="number",
                    default_value=0.8,
                    min_value=0,
                    max_value=1,
                ),
                AgentParameter(
                    name="defect_density_threshold",
                    display_name="Defect Density Threshold",
                    description="Threshold for defect density alerts",
                    param_type="number",
                    default_value=0.05,
                    min_value=0,
                    max_value=1,
                ),
            ],
        ).to_dict()

        # Risk & Issue Management Agent - with detailed parameters
        agents["risk-management-agent"] = AgentConfig(
            catalog_id="risk-management-agent",
            agent_id="risk-management-agent",
            display_name="Risk & Issue Management",
            description="Identifies, assesses, and manages project risks and issues",
            category=AgentCategory.OPERATIONS,
            enabled=True,
            capabilities=[
                "risk_identification",
                "risk_assessment",
                "risk_mitigation",
                "issue_tracking",
                "escalation",
            ],
            parameters=[
                AgentParameter(
                    name="risk_assessment_method",
                    display_name="Risk Assessment Method",
                    description="Method for assessing risk severity",
                    param_type="select",
                    default_value="probability_impact",
                    options=["probability_impact", "monte_carlo", "qualitative", "quantitative"],
                ),
                AgentParameter(
                    name="risk_threshold_high",
                    display_name="High Risk Threshold",
                    description="Score threshold for high-severity risks (probability * impact)",
                    param_type="number",
                    default_value=0.6,
                    min_value=0.3,
                    max_value=0.9,
                ),
                AgentParameter(
                    name="risk_threshold_medium",
                    display_name="Medium Risk Threshold",
                    description="Score threshold for medium-severity risks",
                    param_type="number",
                    default_value=0.3,
                    min_value=0.1,
                    max_value=0.6,
                ),
                AgentParameter(
                    name="auto_escalate_high_risks",
                    display_name="Auto-escalate High Risks",
                    description="Automatically escalate high-severity risks to stakeholders",
                    param_type="boolean",
                    default_value=True,
                ),
                AgentParameter(
                    name="risk_review_frequency",
                    display_name="Risk Review Frequency",
                    description="How often to review and update risk assessments",
                    param_type="select",
                    default_value="weekly",
                    options=["daily", "weekly", "biweekly", "monthly"],
                ),
                AgentParameter(
                    name="issue_sla_hours",
                    display_name="Issue SLA (hours)",
                    description="SLA for issue response time in hours",
                    param_type="number",
                    default_value=24,
                    min_value=1,
                    max_value=168,
                ),
                AgentParameter(
                    name="enable_risk_ai_suggestions",
                    display_name="Enable AI Risk Suggestions",
                    description="Use AI to suggest potential risks and mitigation strategies",
                    param_type="boolean",
                    default_value=True,
                ),
            ],
        ).to_dict()

        # Platform Agents
        agents["compliance-governance-agent"] = AgentConfig(
            catalog_id="compliance-governance-agent",
            agent_id="compliance-governance-agent",
            display_name="Compliance & Regulatory",
            description="Manages compliance requirements and regulatory adherence",
            category=AgentCategory.GOVERNANCE,
            enabled=True,
            capabilities=["compliance_tracking", "audit_management", "regulatory_reporting"],
            parameters=[
                AgentParameter(
                    name="regulations",
                    display_name="Regulations",
                    description="Regulatory frameworks to track",
                    param_type="multiselect",
                    default_value=["GDPR", "SOX", "ISO 27001", "HIPAA", "PCI DSS"],
                    options=["GDPR", "SOX", "ISO 27001", "HIPAA", "PCI DSS"],
                ),
                AgentParameter(
                    name="control_test_frequencies",
                    display_name="Control Test Frequencies",
                    description="JSON map of control test cadence by severity",
                    param_type="string",
                    default_value=(
                        '{"critical":"monthly","high":"quarterly","medium":"semi-annually","low":"annually"}'
                    ),
                ),
            ],
        ).to_dict()

        agents["change-control-agent"] = AgentConfig(
            catalog_id="change-control-agent",
            agent_id="change-control-agent",
            display_name="Change & Configuration",
            description="Manages change requests and configuration management",
            category=AgentCategory.OPERATIONS,
            enabled=True,
            capabilities=["change_management", "configuration_control", "impact_analysis"],
            parameters=[
                AgentParameter(
                    name="change_types",
                    display_name="Change Types",
                    description="Supported change request types",
                    param_type="multiselect",
                    default_value=["normal", "standard", "emergency"],
                    options=["normal", "standard", "emergency"],
                ),
                AgentParameter(
                    name="priority_levels",
                    display_name="Priority Levels",
                    description="Supported change priority levels",
                    param_type="multiselect",
                    default_value=["critical", "high", "medium", "low"],
                    options=["critical", "high", "medium", "low"],
                ),
                AgentParameter(
                    name="baseline_threshold",
                    display_name="Baseline Threshold",
                    description="Threshold to trigger baseline reviews",
                    param_type="number",
                    default_value=0.1,
                    min_value=0,
                    max_value=1,
                ),
                AgentParameter(
                    name="approval_priority_thresholds",
                    display_name="Approval Priority Thresholds",
                    description="Priorities requiring approval workflow",
                    param_type="multiselect",
                    default_value=["critical", "high"],
                    options=["critical", "high", "medium", "low"],
                ),
                AgentParameter(
                    name="approval_change_types",
                    display_name="Approval Change Types",
                    description="Change types requiring approval workflow",
                    param_type="multiselect",
                    default_value=["normal", "emergency"],
                    options=["normal", "standard", "emergency"],
                ),
            ],
        ).to_dict()

        agents["release-deployment-agent"] = AgentConfig(
            catalog_id="release-deployment-agent",
            agent_id="release-deployment-agent",
            display_name="Release & Deployment",
            description="Manages release planning and deployment coordination",
            category=AgentCategory.OPERATIONS,
            enabled=True,
            capabilities=["release_planning", "deployment_coordination", "rollback_management"],
            parameters=[
                AgentParameter(
                    name="environments",
                    display_name="Environments",
                    description="Release environments managed by the agent",
                    param_type="multiselect",
                    default_value=["development", "test", "staging", "production"],
                    options=["development", "test", "staging", "production"],
                ),
                AgentParameter(
                    name="auto_rollback_threshold",
                    display_name="Auto Rollback Threshold",
                    description="Failure threshold that triggers automatic rollback",
                    param_type="number",
                    default_value=0.05,
                    min_value=0,
                    max_value=1,
                ),
                AgentParameter(
                    name="deployment_window_hours",
                    display_name="Deployment Window (hours)",
                    description="Default deployment window length",
                    param_type="number",
                    default_value=4,
                    min_value=1,
                    max_value=24,
                ),
                AgentParameter(
                    name="approval_environments",
                    display_name="Approval Environments",
                    description="Environments requiring approval gates",
                    param_type="multiselect",
                    default_value=["production"],
                    options=["development", "test", "staging", "production"],
                ),
            ],
        ).to_dict()

        agents["knowledge-management-agent"] = AgentConfig(
            catalog_id="knowledge-management-agent",
            agent_id="knowledge-management-agent",
            display_name="Knowledge & Document Management",
            description="Manages project documentation and knowledge base",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["document_management", "knowledge_capture", "search_indexing"],
            parameters=[
                AgentParameter(
                    name="max_summary_length",
                    display_name="Max Summary Length",
                    description="Maximum length for generated summaries",
                    param_type="number",
                    default_value=500,
                    min_value=50,
                    max_value=5000,
                ),
                AgentParameter(
                    name="search_result_limit",
                    display_name="Search Result Limit",
                    description="Maximum number of search results returned",
                    param_type="number",
                    default_value=50,
                    min_value=1,
                    max_value=200,
                ),
                AgentParameter(
                    name="similarity_threshold",
                    display_name="Similarity Threshold",
                    description="Similarity threshold for related documents",
                    param_type="number",
                    default_value=0.75,
                    min_value=0,
                    max_value=1,
                ),
                AgentParameter(
                    name="document_types",
                    display_name="Document Types",
                    description="Supported document categories",
                    param_type="multiselect",
                    default_value=[
                        "charter",
                        "requirements",
                        "design",
                        "test_plan",
                        "meeting_minutes",
                        "lessons_learned",
                        "policy",
                        "procedure",
                        "report",
                    ],
                    options=[
                        "charter",
                        "requirements",
                        "design",
                        "test_plan",
                        "meeting_minutes",
                        "lessons_learned",
                        "policy",
                        "procedure",
                        "report",
                    ],
                ),
            ],
        ).to_dict()

        agents["continuous-improvement-agent"] = AgentConfig(
            catalog_id="continuous-improvement-agent",
            agent_id="continuous-improvement-agent",
            display_name="Continuous Improvement",
            description="Analyzes processes and identifies improvement opportunities",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["process_mining", "bottleneck_detection", "improvement_recommendations"],
            parameters=[
                AgentParameter(
                    name="bottleneck_threshold",
                    display_name="Bottleneck Threshold",
                    description="Threshold for bottleneck detection",
                    param_type="number",
                    default_value=0.2,
                    min_value=0,
                    max_value=1,
                ),
                AgentParameter(
                    name="deviation_threshold",
                    display_name="Deviation Threshold",
                    description="Threshold for process deviation detection",
                    param_type="number",
                    default_value=0.15,
                    min_value=0,
                    max_value=1,
                ),
                AgentParameter(
                    name="min_frequency_threshold",
                    display_name="Minimum Frequency Threshold",
                    description="Minimum event frequency to include in mining",
                    param_type="number",
                    default_value=5,
                    min_value=1,
                    max_value=100,
                ),
                AgentParameter(
                    name="mining_algorithms",
                    display_name="Mining Algorithms",
                    description="Process mining algorithms available",
                    param_type="multiselect",
                    default_value=["alpha_miner", "heuristic_miner", "fuzzy_miner"],
                    options=["alpha_miner", "heuristic_miner", "fuzzy_miner"],
                ),
            ],
        ).to_dict()

        agents["stakeholder-communications-agent"] = AgentConfig(
            catalog_id="stakeholder-communications-agent",
            agent_id="stakeholder-communications-agent",
            display_name="Stakeholder & Communications",
            description="Manages stakeholder engagement and communications",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["stakeholder_mapping", "communication_planning", "reporting"],
            parameters=[
                AgentParameter(
                    name="communication_channels",
                    display_name="Communication Channels",
                    description="Default communication channels",
                    param_type="multiselect",
                    default_value=["email", "teams", "slack", "sms", "portal"],
                    options=["email", "teams", "slack", "sms", "portal"],
                ),
                AgentParameter(
                    name="engagement_levels",
                    display_name="Engagement Levels",
                    description="Supported engagement levels",
                    param_type="multiselect",
                    default_value=["high", "medium", "low", "minimal"],
                    options=["high", "medium", "low", "minimal"],
                ),
                AgentParameter(
                    name="sentiment_threshold",
                    display_name="Sentiment Threshold",
                    description="Threshold for negative sentiment alerts",
                    param_type="number",
                    default_value=-0.3,
                    min_value=-1,
                    max_value=1,
                ),
            ],
        ).to_dict()

        agents["analytics-insights-agent"] = AgentConfig(
            catalog_id="analytics-insights-agent",
            agent_id="analytics-insights-agent",
            display_name="Analytics & Insights",
            description="Provides analytics, dashboards, and business insights",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["data_analysis", "trend_detection", "predictive_analytics"],
            parameters=[
                AgentParameter(
                    name="refresh_interval_minutes",
                    display_name="Refresh Interval (minutes)",
                    description="Interval between analytics refresh cycles",
                    param_type="number",
                    default_value=60,
                    min_value=5,
                    max_value=1440,
                ),
                AgentParameter(
                    name="prediction_confidence_threshold",
                    display_name="Prediction Confidence Threshold",
                    description="Minimum confidence for predictions",
                    param_type="number",
                    default_value=0.75,
                    min_value=0,
                    max_value=1,
                ),
                AgentParameter(
                    name="max_dashboard_widgets",
                    display_name="Max Dashboard Widgets",
                    description="Maximum widgets per dashboard",
                    param_type="number",
                    default_value=20,
                    min_value=1,
                    max_value=100,
                ),
            ],
        ).to_dict()

        agents["data-synchronisation-agent"] = AgentConfig(
            catalog_id="data-synchronisation-agent",
            agent_id="data-synchronisation-agent",
            display_name="Data Synchronization & Quality",
            description="Ensures data quality and synchronization across systems",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["data_validation", "sync_management", "quality_rules"],
            parameters=[
                AgentParameter(
                    name="sync_latency_sla_seconds",
                    display_name="Sync Latency SLA (seconds)",
                    description="Target latency for data synchronization",
                    param_type="number",
                    default_value=60,
                    min_value=1,
                    max_value=3600,
                ),
                AgentParameter(
                    name="duplicate_confidence_threshold",
                    display_name="Duplicate Confidence Threshold",
                    description="Confidence threshold for duplicate detection",
                    param_type="number",
                    default_value=0.85,
                    min_value=0,
                    max_value=1,
                ),
                AgentParameter(
                    name="conflict_resolution_strategy",
                    display_name="Conflict Resolution Strategy",
                    description="Default strategy for resolving sync conflicts",
                    param_type="select",
                    default_value="last_write_wins",
                    options=["last_write_wins", "source_priority", "manual_review"],
                ),
            ],
        ).to_dict()

        agents["workspace-setup-agent"] = AgentConfig(
            catalog_id="workspace-setup-agent",
            agent_id="workspace-setup-agent",
            display_name="Workspace Setup",
            description="Initialises project workspaces and validates connector configuration before delivery begins",
            category=AgentCategory.GOVERNANCE,
            enabled=True,
            capabilities=["workspace_init", "connector_validation", "external_provisioning", "methodology_bootstrap"],
            parameters=[
                AgentParameter(
                    name="require_approval_for_provisioning",
                    display_name="Require Approval for Provisioning",
                    description="Require approval before provisioning external workspace assets",
                    param_type="boolean",
                    default_value=True,
                ),
                AgentParameter(
                    name="max_connector_validation_retries",
                    display_name="Max Connector Validation Retries",
                    description="Maximum retries for connector validation checks",
                    param_type="number",
                    default_value=3,
                    min_value=0,
                    max_value=10,
                ),
            ],
        ).to_dict()

        agents["system-health-agent"] = AgentConfig(
            catalog_id="system-health-agent",
            agent_id="system-health-agent",
            display_name="System Health & Monitoring",
            description="Monitors system health and performance",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["health_monitoring", "alerting", "performance_metrics"],
            parameters=[
                AgentParameter(
                    name="alert_threshold_error_rate",
                    display_name="Alert Threshold Error Rate",
                    description="Error rate threshold that triggers alerts",
                    param_type="number",
                    default_value=0.05,
                    min_value=0,
                    max_value=1,
                ),
                AgentParameter(
                    name="alert_threshold_response_time_ms",
                    display_name="Alert Threshold Response Time (ms)",
                    description="Response time threshold that triggers alerts",
                    param_type="number",
                    default_value=1000,
                    min_value=50,
                    max_value=10000,
                ),
                AgentParameter(
                    name="metrics_retention_days",
                    display_name="Metrics Retention (days)",
                    description="Retention period for metrics data",
                    param_type="number",
                    default_value=90,
                    min_value=1,
                    max_value=365,
                ),
            ],
        ).to_dict()

        return agents

    def _load(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.store_path.read_text()))

    def _save(self, data: dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(data, indent=2))

    # Agent CRUD operations
    def list_agents(self) -> list[AgentConfig]:
        """List all agent configurations."""
        data = self._load()
        return [AgentConfig.from_dict(a) for a in data.get("agents", {}).values()]

    def get_agent(self, catalog_id: str) -> AgentConfig | None:
        """Get a specific agent configuration."""
        data = self._load()
        agent_data = data.get("agents", {}).get(catalog_id)
        if not agent_data:
            return None
        return AgentConfig.from_dict(agent_data)

    def update_agent(
        self, catalog_id: str, updates: dict[str, Any], updated_by: str | None = None
    ) -> AgentConfig | None:
        """Update an agent configuration."""
        data = self._load()
        if catalog_id not in data.get("agents", {}):
            return None

        agent_data = data["agents"][catalog_id]
        for key, value in updates.items():
            if key == "parameters" and isinstance(value, list):
                # Handle parameter updates
                agent_data["parameters"] = value
            elif key != "catalog_id":  # Don't allow changing catalog_id
                agent_data[key] = value

        agent_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        agent_data["updated_by"] = updated_by

        data["agents"][catalog_id] = agent_data
        self._save(data)

        return AgentConfig.from_dict(agent_data)

    # Project-specific config operations
    def get_project_agent_config(self, project_id: str, agent_id: str) -> ProjectAgentConfig | None:
        """Get project-specific agent configuration."""
        data = self._load()
        project_configs = data.get("project_configs", {}).get(project_id, {})
        config_data = project_configs.get(agent_id)
        if not config_data:
            return None
        return ProjectAgentConfig.from_dict(config_data)

    def set_project_agent_config(
        self,
        project_id: str,
        agent_id: str,
        enabled: bool,
        parameter_overrides: dict[str, Any] | None = None,
        updated_by: str | None = None,
    ) -> ProjectAgentConfig:
        """Set project-specific agent configuration."""
        data = self._load()
        if "project_configs" not in data:
            data["project_configs"] = {}
        if project_id not in data["project_configs"]:
            data["project_configs"][project_id] = {}

        config = ProjectAgentConfig(
            project_id=project_id,
            agent_id=agent_id,
            enabled=enabled,
            parameter_overrides=parameter_overrides or {},
            updated_at=datetime.now(timezone.utc).isoformat(),
            updated_by=updated_by,
        )

        data["project_configs"][project_id][agent_id] = config.to_dict()
        self._save(data)

        return config

    def list_project_agent_configs(self, project_id: str) -> list[ProjectAgentConfig]:
        """List all agent configurations for a project."""
        data = self._load()
        project_configs = data.get("project_configs", {}).get(project_id, {})
        return [ProjectAgentConfig.from_dict(c) for c in project_configs.values()]

    def is_agent_enabled_for_project(self, project_id: str, agent_id: str) -> bool:
        """Check if an agent is enabled for a specific project."""
        # First check project-specific config
        project_config = self.get_project_agent_config(project_id, agent_id)
        if project_config is not None:
            return project_config.enabled

        # Fall back to global agent config
        # Find agent by agent_id (not catalog_id)
        for agent in self.list_agents():
            if agent.agent_id == agent_id:
                return agent.enabled

        return True  # Default to enabled if not found

    def get_enabled_agents_for_project(self, project_id: str) -> list[AgentConfig]:
        """Get all agents that are enabled for a specific project."""
        agents = self.list_agents()
        enabled_agents = []

        for agent in agents:
            if self.is_agent_enabled_for_project(project_id, agent.agent_id):
                enabled_agents.append(agent)

        return enabled_agents

    # RBAC operations
    def sync_user_roles(
        self,
        *,
        user_id: str,
        tenant_id: str,
        roles: list[str],
        display_name: str | None = None,
        email: str | None = None,
    ) -> None:
        """Persist authenticated user roles for RBAC decisions."""
        self.rbac_store.sync_user_roles(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
            display_name=display_name,
            email=email,
        )

    def can_user_configure_agents(self, user_id: str, tenant_id: str) -> bool:
        """Check if user has permission to configure agents."""
        return self.rbac_store.can_user_configure_agents(user_id, tenant_id)


# Global instance for easy access
_store_instance: AgentConfigStore | None = None


def get_agent_config_store(store_path: Path | None = None) -> AgentConfigStore:
    """Get or create the global agent config store instance."""
    global _store_instance
    if _store_instance is None:
        if store_path is None:
            env_path = os.getenv("AGENT_CONFIG_STORE_PATH")
            if env_path:
                store_path = Path(env_path)
            else:
                # Default path in data directory
                store_path = Path(__file__).parents[4] / "data" / "agent_config.json"
        database_url = os.getenv("AGENT_CONFIG_DATABASE_URL") or os.getenv("DATABASE_URL")
        if not database_url:
            default_db_path = Path(__file__).parents[4] / "data" / "agent_config_rbac.db"
            default_db_path.parent.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{default_db_path}"
        _store_instance = AgentConfigStore(store_path, database_url)
    return _store_instance


def reset_store_instance() -> None:
    """Reset the global store instance (useful for testing)."""
    global _store_instance
    _store_instance = None

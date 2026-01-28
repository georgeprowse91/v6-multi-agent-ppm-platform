"""
Agent Configuration Service

Provides CRUD operations for agent enablement and configuration parameters.
Uses a JSON-backed file store for persistence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, cast


class AgentCategory(str, Enum):
    """Agent categories for grouping."""
    CORE = "core"
    PORTFOLIO = "portfolio"
    DELIVERY = "delivery"
    OPERATIONS = "operations"
    PLATFORM = "platform"
    GOVERNANCE = "governance"


class UserRole(str, Enum):
    """User roles for permission checks."""
    ADMIN = "admin"
    PM = "pm"          # Project Manager
    MEMBER = "member"


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
    min_value: float | None = None    # For number type
    max_value: float | None = None    # For number type
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentParameter":
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
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_id": self.catalog_id,
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value if isinstance(self.category, AgentCategory) else self.category,
            "enabled": self.enabled,
            "parameters": [p.to_dict() for p in self.parameters],
            "capabilities": self.capabilities,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfig":
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
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            updated_by=data.get("updated_by"),
        )


@dataclass
class ProjectAgentConfig:
    """Project-specific agent configuration (enablement + parameter overrides)."""
    project_id: str
    agent_id: str
    enabled: bool = True
    parameter_overrides: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectAgentConfig":
        return cls(**data)


@dataclass
class DevUserProfile:
    """Development user profile for role-based access control stub."""
    user_id: str
    name: str
    email: str
    role: UserRole
    tenant_id: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "tenant_id": self.tenant_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DevUserProfile":
        role = data.get("role", UserRole.MEMBER)
        if isinstance(role, str):
            role = UserRole(role)
        return cls(
            user_id=data["user_id"],
            name=data["name"],
            email=data["email"],
            role=role,
            tenant_id=data.get("tenant_id", "default"),
        )


class AgentConfigStore:
    """JSON-backed store for agent configurations."""

    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._initialize_store()

    def _initialize_store(self) -> None:
        """Initialize store with default agent configurations."""
        initial_data = {
            "agents": self._get_default_agents(),
            "project_configs": {},
            "dev_users": self._get_default_dev_users(),
        }
        self._save(initial_data)

    def _get_default_dev_users(self) -> dict[str, Any]:
        """Return default development user profiles."""
        return {
            "admin": DevUserProfile(
                user_id="admin",
                name="Admin User",
                email="admin@example.com",
                role=UserRole.ADMIN,
            ).to_dict(),
            "pm": DevUserProfile(
                user_id="pm",
                name="Project Manager",
                email="pm@example.com",
                role=UserRole.PM,
            ).to_dict(),
            "member": DevUserProfile(
                user_id="member",
                name="Team Member",
                email="member@example.com",
                role=UserRole.MEMBER,
            ).to_dict(),
        }

    def _get_default_agents(self) -> dict[str, Any]:
        """Return default agent configurations."""
        agents = {}

        # Core Agents
        agents["agent-01-intent-router"] = AgentConfig(
            catalog_id="agent-01-intent-router",
            agent_id="intent-router",
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

        agents["agent-02-response-orchestration"] = AgentConfig(
            catalog_id="agent-02-response-orchestration",
            agent_id="response-orchestration",
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
        agents["agent-03-approval-workflow"] = AgentConfig(
            catalog_id="agent-03-approval-workflow",
            agent_id="agent_003_approval_workflow",
            display_name="Approval Workflow",
            description="Manages approval workflows and gate reviews",
            category=AgentCategory.GOVERNANCE,
            enabled=True,
            capabilities=["approval_management", "gate_review", "escalation"],
        ).to_dict()

        # Portfolio Agents
        agents["agent-04-demand-intake"] = AgentConfig(
            catalog_id="agent-04-demand-intake",
            agent_id="demand-intake",
            display_name="Demand Intake",
            description="Handles intake of new project demands and requests",
            category=AgentCategory.PORTFOLIO,
            enabled=True,
            capabilities=["demand_capture", "prioritization", "initial_assessment"],
        ).to_dict()

        agents["agent-05-business-case-investment"] = AgentConfig(
            catalog_id="agent-05-business-case-investment",
            agent_id="business-case-investment",
            display_name="Business Case & Investment",
            description="Analyzes business cases and investment decisions",
            category=AgentCategory.PORTFOLIO,
            enabled=True,
            capabilities=["roi_analysis", "benefit_tracking", "investment_modeling"],
        ).to_dict()

        agents["agent-06-portfolio-strategy-optimisation"] = AgentConfig(
            catalog_id="agent-06-portfolio-strategy-optimisation",
            agent_id="portfolio-strategy-optimization",
            display_name="Portfolio Strategy & Optimization",
            description="Optimizes portfolio mix and strategic alignment",
            category=AgentCategory.PORTFOLIO,
            enabled=True,
            capabilities=["portfolio_analysis", "resource_optimization", "strategic_alignment"],
        ).to_dict()

        # Delivery Agents
        agents["agent-07-program-management"] = AgentConfig(
            catalog_id="agent-07-program-management",
            agent_id="program-management",
            display_name="Program Management",
            description="Manages programs and cross-project coordination",
            category=AgentCategory.DELIVERY,
            enabled=True,
            capabilities=["program_planning", "dependency_management", "benefit_realization"],
        ).to_dict()

        agents["agent-08-project-definition-scope"] = AgentConfig(
            catalog_id="agent-08-project-definition-scope",
            agent_id="project-definition",
            display_name="Project Definition & Scope",
            description="Defines project scope and deliverables",
            category=AgentCategory.DELIVERY,
            enabled=True,
            capabilities=["scope_definition", "wbs_creation", "deliverable_tracking"],
        ).to_dict()

        agents["agent-09-lifecycle-governance"] = AgentConfig(
            catalog_id="agent-09-lifecycle-governance",
            agent_id="project-lifecycle-governance",
            display_name="Project Lifecycle & Governance",
            description="Manages project lifecycle and governance processes",
            category=AgentCategory.GOVERNANCE,
            enabled=True,
            capabilities=["lifecycle_management", "gate_reviews", "health_monitoring"],
        ).to_dict()

        # Schedule & Planning Agent - with detailed parameters
        agents["agent-10-schedule-planning"] = AgentConfig(
            catalog_id="agent-10-schedule-planning",
            agent_id="schedule-planning",
            display_name="Schedule & Planning",
            description="Manages project schedules, timelines, and critical path analysis",
            category=AgentCategory.DELIVERY,
            enabled=True,
            capabilities=["schedule_creation", "critical_path_analysis", "milestone_tracking", "dependency_management", "baseline_management"],
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
            ],
        ).to_dict()

        agents["agent-11-resource-capacity"] = AgentConfig(
            catalog_id="agent-11-resource-capacity",
            agent_id="resource-capacity-management",
            display_name="Resource & Capacity",
            description="Manages resource allocation and capacity planning",
            category=AgentCategory.DELIVERY,
            enabled=True,
            capabilities=["resource_allocation", "capacity_planning", "skill_matching"],
        ).to_dict()

        # Financial Management Agent - with detailed parameters
        agents["agent-12-financial-management"] = AgentConfig(
            catalog_id="agent-12-financial-management",
            agent_id="financial-management",
            display_name="Financial Management",
            description="Manages project finances, budgets, forecasts, and cost tracking",
            category=AgentCategory.PORTFOLIO,
            enabled=True,
            capabilities=["budget_management", "cost_tracking", "forecasting", "variance_analysis", "evm_metrics"],
            parameters=[
                AgentParameter(
                    name="currency",
                    display_name="Default Currency",
                    description="Default currency for financial calculations",
                    param_type="select",
                    default_value="USD",
                    options=["USD", "EUR", "GBP", "AUD", "CAD", "JPY"],
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
        agents["agent-13-vendor-procurement"] = AgentConfig(
            catalog_id="agent-13-vendor-procurement",
            agent_id="agent_013",
            display_name="Vendor & Procurement",
            description="Manages vendor relationships and procurement processes",
            category=AgentCategory.OPERATIONS,
            enabled=True,
            capabilities=["vendor_management", "contract_tracking", "procurement"],
        ).to_dict()

        agents["agent-14-quality-management"] = AgentConfig(
            catalog_id="agent-14-quality-management",
            agent_id="agent_014",
            display_name="Quality Management",
            description="Manages quality assurance and quality control processes",
            category=AgentCategory.OPERATIONS,
            enabled=True,
            capabilities=["quality_planning", "defect_tracking", "quality_metrics"],
        ).to_dict()

        # Risk & Issue Management Agent - with detailed parameters
        agents["agent-15-risk-issue-management"] = AgentConfig(
            catalog_id="agent-15-risk-issue-management",
            agent_id="agent_015",
            display_name="Risk & Issue Management",
            description="Identifies, assesses, and manages project risks and issues",
            category=AgentCategory.OPERATIONS,
            enabled=True,
            capabilities=["risk_identification", "risk_assessment", "risk_mitigation", "issue_tracking", "escalation"],
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
        agents["agent-16-compliance-regulatory"] = AgentConfig(
            catalog_id="agent-16-compliance-regulatory",
            agent_id="agent_016",
            display_name="Compliance & Regulatory",
            description="Manages compliance requirements and regulatory adherence",
            category=AgentCategory.GOVERNANCE,
            enabled=True,
            capabilities=["compliance_tracking", "audit_management", "regulatory_reporting"],
        ).to_dict()

        agents["agent-17-change-configuration"] = AgentConfig(
            catalog_id="agent-17-change-configuration",
            agent_id="agent_017",
            display_name="Change & Configuration",
            description="Manages change requests and configuration management",
            category=AgentCategory.OPERATIONS,
            enabled=True,
            capabilities=["change_management", "configuration_control", "impact_analysis"],
        ).to_dict()

        agents["agent-18-release-deployment"] = AgentConfig(
            catalog_id="agent-18-release-deployment",
            agent_id="agent_018",
            display_name="Release & Deployment",
            description="Manages release planning and deployment coordination",
            category=AgentCategory.OPERATIONS,
            enabled=True,
            capabilities=["release_planning", "deployment_coordination", "rollback_management"],
        ).to_dict()

        agents["agent-19-knowledge-document-management"] = AgentConfig(
            catalog_id="agent-19-knowledge-document-management",
            agent_id="agent_019",
            display_name="Knowledge & Document Management",
            description="Manages project documentation and knowledge base",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["document_management", "knowledge_capture", "search_indexing"],
        ).to_dict()

        agents["agent-20-continuous-improvement-process-mining"] = AgentConfig(
            catalog_id="agent-20-continuous-improvement-process-mining",
            agent_id="agent_020",
            display_name="Continuous Improvement",
            description="Analyzes processes and identifies improvement opportunities",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["process_mining", "bottleneck_detection", "improvement_recommendations"],
        ).to_dict()

        agents["agent-21-stakeholder-comms"] = AgentConfig(
            catalog_id="agent-21-stakeholder-comms",
            agent_id="agent_021",
            display_name="Stakeholder & Communications",
            description="Manages stakeholder engagement and communications",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["stakeholder_mapping", "communication_planning", "reporting"],
        ).to_dict()

        agents["agent-22-analytics-insights"] = AgentConfig(
            catalog_id="agent-22-analytics-insights",
            agent_id="agent_022",
            display_name="Analytics & Insights",
            description="Provides analytics, dashboards, and business insights",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["data_analysis", "trend_detection", "predictive_analytics"],
        ).to_dict()

        agents["agent-23-data-synchronisation-quality"] = AgentConfig(
            catalog_id="agent-23-data-synchronisation-quality",
            agent_id="agent_023",
            display_name="Data Synchronization & Quality",
            description="Ensures data quality and synchronization across systems",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["data_validation", "sync_management", "quality_rules"],
        ).to_dict()

        agents["agent-24-workflow-process-engine"] = AgentConfig(
            catalog_id="agent-24-workflow-process-engine",
            agent_id="agent_024",
            display_name="Workflow & Process Engine",
            description="Executes and manages automated workflows",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["workflow_execution", "process_automation", "task_routing"],
        ).to_dict()

        agents["agent-25-system-health-monitoring"] = AgentConfig(
            catalog_id="agent-25-system-health-monitoring",
            agent_id="agent_025",
            display_name="System Health & Monitoring",
            description="Monitors system health and performance",
            category=AgentCategory.PLATFORM,
            enabled=True,
            capabilities=["health_monitoring", "alerting", "performance_metrics"],
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

    def update_agent(self, catalog_id: str, updates: dict[str, Any], updated_by: str | None = None) -> AgentConfig | None:
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

        agent_data["updated_at"] = datetime.utcnow().isoformat()
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
            updated_at=datetime.utcnow().isoformat(),
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

    # Dev user operations (stub for RBAC)
    def get_dev_user(self, user_id: str) -> DevUserProfile | None:
        """Get a development user profile."""
        data = self._load()
        user_data = data.get("dev_users", {}).get(user_id)
        if not user_data:
            return None
        return DevUserProfile.from_dict(user_data)

    def list_dev_users(self) -> list[DevUserProfile]:
        """List all development user profiles."""
        data = self._load()
        return [DevUserProfile.from_dict(u) for u in data.get("dev_users", {}).values()]

    def can_user_configure_agents(self, user_id: str) -> bool:
        """Check if user has permission to configure agents."""
        user = self.get_dev_user(user_id)
        if not user:
            return False
        # Only admin and PM roles can configure agents
        return user.role in (UserRole.ADMIN, UserRole.PM)


# Global instance for easy access
_store_instance: AgentConfigStore | None = None


def get_agent_config_store(store_path: Path | None = None) -> AgentConfigStore:
    """Get or create the global agent config store instance."""
    global _store_instance
    if _store_instance is None:
        if store_path is None:
            # Default path in data directory
            store_path = Path(__file__).parents[4] / "data" / "agent_config.json"
        _store_instance = AgentConfigStore(store_path)
    return _store_instance


def reset_store_instance() -> None:
    """Reset the global store instance (useful for testing)."""
    global _store_instance
    _store_instance = None

"""
Multi-Agent PPM Platform - All 25 Agents

This module contains all 25 specialized agents for the PPM platform.
"""

# Core Orchestration (Agents 1-2)
from src.agents.core.orchestration.intent_router_agent import IntentRouterAgent
from src.agents.core.orchestration.response_orchestration_agent import ResponseOrchestrationAgent

# Governance (Agents 3, 16)
from src.agents.governance.workflows.approval_workflow_agent import ApprovalWorkflowAgent
from src.agents.governance.compliance_regulatory.compliance_regulatory_agent import ComplianceRegulatoryAgent

# Portfolio Management (Agents 4, 5, 6, 12)
from src.agents.portfolio.intake.demand_intake_agent import DemandIntakeAgent
from src.agents.portfolio.investment_analysis.business_case_investment_agent import BusinessCaseInvestmentAgent
from src.agents.portfolio.strategy_optimization.portfolio_strategy_agent import PortfolioStrategyAgent
from src.agents.portfolio.financial_management.financial_management_agent import FinancialManagementAgent

# Delivery (Agents 7, 8, 9, 10, 11)
from src.agents.delivery.program_management.program_management_agent import ProgramManagementAgent
from src.agents.delivery.project_definition.project_definition_agent import ProjectDefinitionAgent
from src.agents.delivery.lifecycle_governance.project_lifecycle_agent import ProjectLifecycleAgent
from src.agents.delivery.planning_scheduling.schedule_planning_agent import SchedulePlanningAgent
from src.agents.delivery.resource_capacity.resource_capacity_agent import ResourceCapacityAgent

# Operations (Agents 13, 14, 15, 17, 21)
from src.agents.operations.vendor_procurement.vendor_procurement_agent import VendorProcurementAgent
from src.agents.operations.quality_management.quality_management_agent import QualityManagementAgent
from src.agents.operations.risk_management.risk_management_agent import RiskManagementAgent
from src.agents.operations.change_configuration.change_configuration_agent import ChangeConfigurationAgent
from src.agents.operations.stakeholder_communications.stakeholder_communications_agent import StakeholderCommunicationsAgent

# Platform (Agents 18, 19, 20, 22, 23, 24, 25)
from src.agents.platform.release_deployment.release_deployment_agent import ReleaseDeploymentAgent
from src.agents.platform.knowledge_management.knowledge_management_agent import KnowledgeManagementAgent
from src.agents.platform.process_mining.process_mining_agent import ProcessMiningAgent
from src.agents.platform.analytics_insights.analytics_insights_agent import AnalyticsInsightsAgent
from src.agents.platform.data_sync.data_sync_agent import DataSyncAgent
from src.agents.platform.workflow_engine.workflow_engine_agent import WorkflowEngineAgent
from src.agents.platform.system_health.system_health_agent import SystemHealthAgent

__all__ = [
    # Core Orchestration
    "IntentRouterAgent",
    "ResponseOrchestrationAgent",
    # Governance
    "ApprovalWorkflowAgent",
    "ComplianceRegulatoryAgent",
    # Portfolio Management
    "DemandIntakeAgent",
    "BusinessCaseInvestmentAgent",
    "PortfolioStrategyAgent",
    "FinancialManagementAgent",
    # Delivery
    "ProgramManagementAgent",
    "ProjectDefinitionAgent",
    "ProjectLifecycleAgent",
    "SchedulePlanningAgent",
    "ResourceCapacityAgent",
    # Operations
    "VendorProcurementAgent",
    "QualityManagementAgent",
    "RiskManagementAgent",
    "ChangeConfigurationAgent",
    "StakeholderCommunicationsAgent",
    # Platform
    "ReleaseDeploymentAgent",
    "KnowledgeManagementAgent",
    "ProcessMiningAgent",
    "AnalyticsInsightsAgent",
    "DataSyncAgent",
    "WorkflowEngineAgent",
    "SystemHealthAgent",
]

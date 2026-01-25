"""
Agent Orchestrator - Manages agent lifecycle and routing
"""

import logging
from pathlib import Path
from typing import Any, cast

from tools.runtime_paths import bootstrap_runtime_paths

bootstrap_runtime_paths()

# Core Orchestration
from intent_router_agent import IntentRouterAgent
from response_orchestration_agent import ResponseOrchestrationAgent
from project_lifecycle_agent import ProjectLifecycleAgent
from schedule_planning_agent import SchedulePlanningAgent

# Delivery
from program_management_agent import ProgramManagementAgent
from project_definition_agent import ProjectDefinitionAgent
from resource_capacity_agent import ResourceCapacityAgent
from compliance_regulatory_agent import ComplianceRegulatoryAgent

# Governance
from approval_workflow_agent import ApprovalWorkflowAgent
from change_configuration_agent import ChangeConfigurationAgent
from quality_management_agent import QualityManagementAgent
from risk_management_agent import RiskManagementAgent
from stakeholder_communications_agent import StakeholderCommunicationsAgent

# Operations
from vendor_procurement_agent import VendorProcurementAgent
from analytics_insights_agent import AnalyticsInsightsAgent
from data_sync_agent import DataSyncAgent
from knowledge_management_agent import KnowledgeManagementAgent
from process_mining_agent import ProcessMiningAgent

# Platform
from release_deployment_agent import ReleaseDeploymentAgent
from system_health_agent import SystemHealthAgent
from workflow_engine_agent import WorkflowEngineAgent
from financial_management_agent import FinancialManagementAgent

# Portfolio Management
from demand_intake_agent import DemandIntakeAgent
from business_case_investment_agent import BusinessCaseInvestmentAgent
from portfolio_strategy_agent import PortfolioStrategyAgent

logger = logging.getLogger(__name__)
DEFAULT_POLICY_BUNDLE_PATH = (
    Path(__file__).resolve().parents[1] / "policies" / "bundles" / "default-policy-bundle.yaml"
)


class AgentOrchestrator:
    """
    Central orchestrator for all PPM agents.

    Manages agent lifecycle, routing, and coordination.
    """

    def __init__(self):
        self.agents = {}
        self.initialized = False
        self.intent_router = None
        self.response_orchestrator = None
        self.policy_bundle_path = DEFAULT_POLICY_BUNDLE_PATH

    async def initialize(self):
        """Initialize all 25 agents."""
        logger.info("Initializing Agent Orchestrator...")
        logger.info("Using policy bundle: %s", self.policy_bundle_path)

        # Initialize core orchestration agents (Agents 1-2)
        self.intent_router = IntentRouterAgent()
        await self.intent_router.initialize()
        self.agents["agent_001_intent_router"] = self.intent_router

        self.response_orchestrator = ResponseOrchestrationAgent()
        await self.response_orchestrator.initialize()
        self.agents["agent_002_response_orchestration"] = self.response_orchestrator

        # Load all other agents
        await self._load_governance_agents()  # Agents 3, 16
        await self._load_portfolio_agents()  # Agents 4, 5, 6, 12
        await self._load_delivery_agents()  # Agents 7, 8, 9, 10, 11
        await self._load_operations_agents()  # Agents 13, 14, 15, 17, 21
        await self._load_platform_agents()  # Agents 18, 19, 20, 22, 23, 24, 25

        self.initialized = True
        logger.info(f"Orchestrator initialized with {len(self.agents)} agents")

    async def _load_governance_agents(self):
        """Initialize governance agents."""
        logger.info("Loading governance agents...")

        # Agent 3: Approval Workflow

        approval_agent = ApprovalWorkflowAgent()

        await approval_agent.initialize()

        self.agents[approval_agent.agent_id] = approval_agent

        # Agent 16: Compliance & Regulatory

        compliance_agent = ComplianceRegulatoryAgent()
        await compliance_agent.initialize()
        self.agents[compliance_agent.agent_id] = compliance_agent

        logger.info("Governance agents loaded")

    async def _load_portfolio_agents(self):
        """Initialize portfolio management agents."""
        logger.info("Loading portfolio agents...")

        # Agent 4: Demand & Intake
        demand_agent = DemandIntakeAgent()
        await demand_agent.initialize()
        self.agents[demand_agent.agent_id] = demand_agent

        # Agent 5: Business Case & Investment Analysis
        business_case_agent = BusinessCaseInvestmentAgent()
        await business_case_agent.initialize()
        self.agents[business_case_agent.agent_id] = business_case_agent

        # Agent 6: Portfolio Strategy & Optimization
        portfolio_strategy_agent = PortfolioStrategyAgent()
        await portfolio_strategy_agent.initialize()
        self.agents[portfolio_strategy_agent.agent_id] = portfolio_strategy_agent

        # Agent 12: Financial Management
        financial_agent = FinancialManagementAgent()
        await financial_agent.initialize()
        self.agents[financial_agent.agent_id] = financial_agent

        logger.info("Portfolio agents loaded")

    async def _load_delivery_agents(self):
        """Initialize delivery agents."""
        logger.info("Loading delivery agents...")

        # Agent 7: Program Management
        program_agent = ProgramManagementAgent()
        await program_agent.initialize()
        self.agents[program_agent.agent_id] = program_agent

        # Agent 8: Project Definition & Scope
        project_definition_agent = ProjectDefinitionAgent()
        await project_definition_agent.initialize()
        self.agents[project_definition_agent.agent_id] = project_definition_agent

        # Agent 9: Project Lifecycle & Governance
        lifecycle_agent = ProjectLifecycleAgent()
        await lifecycle_agent.initialize()
        self.agents[lifecycle_agent.agent_id] = lifecycle_agent

        # Agent 10: Schedule & Planning
        schedule_agent = SchedulePlanningAgent()
        await schedule_agent.initialize()
        self.agents[schedule_agent.agent_id] = schedule_agent

        # Agent 11: Resource & Capacity Management
        resource_agent = ResourceCapacityAgent()
        await resource_agent.initialize()
        self.agents[resource_agent.agent_id] = resource_agent

        logger.info("Delivery agents loaded")

    async def _load_operations_agents(self):
        """Initialize operations agents."""
        logger.info("Loading operations agents...")

        # Agent 13: Vendor & Procurement Management
        vendor_agent = VendorProcurementAgent()
        await vendor_agent.initialize()
        self.agents[vendor_agent.agent_id] = vendor_agent

        # Agent 14: Quality Management
        quality_agent = QualityManagementAgent()
        await quality_agent.initialize()
        self.agents[quality_agent.agent_id] = quality_agent

        # Agent 15: Risk Management
        risk_agent = RiskManagementAgent()
        await risk_agent.initialize()
        self.agents[risk_agent.agent_id] = risk_agent

        # Agent 17: Change & Configuration Management
        change_agent = ChangeConfigurationAgent()
        await change_agent.initialize()
        self.agents[change_agent.agent_id] = change_agent

        # Agent 21: Stakeholder & Communications Management
        stakeholder_agent = StakeholderCommunicationsAgent()
        await stakeholder_agent.initialize()
        self.agents[stakeholder_agent.agent_id] = stakeholder_agent

        logger.info("Operations agents loaded")

    async def _load_platform_agents(self):
        """Initialize platform agents."""
        logger.info("Loading platform agents...")

        # Agent 18: Release & Deployment
        release_agent = ReleaseDeploymentAgent()
        await release_agent.initialize()
        self.agents[release_agent.agent_id] = release_agent

        # Agent 19: Knowledge & Document Management
        knowledge_agent = KnowledgeManagementAgent()
        await knowledge_agent.initialize()
        self.agents[knowledge_agent.agent_id] = knowledge_agent

        # Agent 20: Continuous Improvement & Process Mining
        process_mining_agent = ProcessMiningAgent()
        await process_mining_agent.initialize()
        self.agents[process_mining_agent.agent_id] = process_mining_agent

        # Agent 22: Analytics & Insights
        analytics_agent = AnalyticsInsightsAgent()
        await analytics_agent.initialize()
        self.agents[analytics_agent.agent_id] = analytics_agent

        # Agent 23: Data Synchronization & Consistency
        data_sync_agent = DataSyncAgent()
        await data_sync_agent.initialize()
        self.agents[data_sync_agent.agent_id] = data_sync_agent

        # Agent 24: Workflow & Process Engine
        workflow_agent = WorkflowEngineAgent()
        await workflow_agent.initialize()
        self.agents[workflow_agent.agent_id] = workflow_agent

        # Agent 25: System Health & Monitoring
        health_agent = SystemHealthAgent()
        await health_agent.initialize()
        self.agents[health_agent.agent_id] = health_agent

        logger.info("Platform agents loaded")

    async def process_query(
        self, query: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Process a user query through the full agent pipeline.

        Args:
            query: User's natural language query
            context: Optional context (user_id, session_id, etc.)

        Returns:
            Final aggregated response
        """
        if not self.initialized:
            raise RuntimeError("Orchestrator not initialized")

        assert self.intent_router is not None, "Intent router not initialized"
        assert self.response_orchestrator is not None, "Response orchestrator not initialized"

        # Step 1: Route the query
        intent_result = await self.intent_router.execute(
            {
                "query": query,
                "context": context or {},
            }
        )

        if not intent_result["success"]:
            return {
                "success": False,
                "error": "Failed to route query",
                "details": intent_result,
            }

        # Step 2: Orchestrate response
        orchestration_result = await self.response_orchestrator.execute(
            {
                "routing": intent_result["data"]["routing"],
                "parameters": intent_result["data"]["parameters"],
                "query": query,
            }
        )

        return cast(dict[str, Any], orchestration_result)

    def get_agent(self, agent_id: str):
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def get_agent_count(self) -> int:
        """Get total number of loaded agents."""
        return len(self.agents)

    def list_agents(self) -> list:
        """List all loaded agents."""
        return [
            {
                "agent_id": agent_id,
                "capabilities": agent.get_capabilities(),
            }
            for agent_id, agent in self.agents.items()
        ]

    async def cleanup(self):
        """Clean up all agents."""
        logger.info("Cleaning up orchestrator...")
        for agent_id, agent in self.agents.items():
            try:
                await agent.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up agent {agent_id}: {str(e)}")

        self.agents.clear()
        self.initialized = False
        logger.info("Orchestrator cleanup complete")

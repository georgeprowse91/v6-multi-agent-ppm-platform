"""
Agent Orchestrator - Manages agent lifecycle and routing
"""

from typing import Dict, Any, Optional
import logging

# Core Orchestration
from src.agents.core.orchestration.intent_router_agent import IntentRouterAgent
from src.agents.core.orchestration.response_orchestration_agent import ResponseOrchestrationAgent

# Governance
from src.agents.governance.workflows.approval_workflow_agent import ApprovalWorkflowAgent
from src.agents.governance.compliance_regulatory.compliance_regulatory_agent import ComplianceRegulatoryAgent

# Portfolio Management
from src.agents.portfolio.intake.demand_intake_agent import DemandIntakeAgent
from src.agents.portfolio.investment_analysis.business_case_investment_agent import BusinessCaseInvestmentAgent
from src.agents.portfolio.strategy_optimization.portfolio_strategy_agent import PortfolioStrategyAgent
from src.agents.portfolio.financial_management.financial_management_agent import FinancialManagementAgent

# Delivery
from src.agents.delivery.program_management.program_management_agent import ProgramManagementAgent
from src.agents.delivery.project_definition.project_definition_agent import ProjectDefinitionAgent
from src.agents.delivery.lifecycle_governance.project_lifecycle_agent import ProjectLifecycleAgent
from src.agents.delivery.planning_scheduling.schedule_planning_agent import SchedulePlanningAgent
from src.agents.delivery.resource_capacity.resource_capacity_agent import ResourceCapacityAgent

# Operations
from src.agents.operations.vendor_procurement.vendor_procurement_agent import VendorProcurementAgent
from src.agents.operations.quality_management.quality_management_agent import QualityManagementAgent
from src.agents.operations.risk_management.risk_management_agent import RiskManagementAgent
from src.agents.operations.change_configuration.change_configuration_agent import ChangeConfigurationAgent
from src.agents.operations.stakeholder_communications.stakeholder_communications_agent import StakeholderCommunicationsAgent

# Platform
from src.agents.platform.release_deployment.release_deployment_agent import ReleaseDeploymentAgent
from src.agents.platform.knowledge_management.knowledge_management_agent import KnowledgeManagementAgent
from src.agents.platform.process_mining.process_mining_agent import ProcessMiningAgent
from src.agents.platform.analytics_insights.analytics_insights_agent import AnalyticsInsightsAgent
from src.agents.platform.data_sync.data_sync_agent import DataSyncAgent
from src.agents.platform.workflow_engine.workflow_engine_agent import WorkflowEngineAgent
from src.agents.platform.system_health.system_health_agent import SystemHealthAgent

logger = logging.getLogger(__name__)


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

    async def initialize(self):
        """Initialize all 25 agents."""
        logger.info("Initializing Agent Orchestrator...")

        # Initialize core orchestration agents (Agents 1-2)
        self.intent_router = IntentRouterAgent()
        await self.intent_router.initialize()
        self.agents["agent_001_intent_router"] = self.intent_router

        self.response_orchestrator = ResponseOrchestrationAgent()
        await self.response_orchestrator.initialize()
        self.agents["agent_002_response_orchestration"] = self.response_orchestrator

        # Load all other agents
        await self._load_governance_agents()  # Agents 3, 16
        await self._load_portfolio_agents()   # Agents 4, 5, 6, 12
        await self._load_delivery_agents()    # Agents 7, 8, 9, 10, 11
        await self._load_operations_agents()  # Agents 13, 14, 15, 17, 21
        await self._load_platform_agents()    # Agents 18, 19, 20, 22, 23, 24, 25

        self.initialized = True
        logger.info(f"Orchestrator initialized with {len(self.agents)} agents")

    async def _load_governance_agents(self):
        """Initialize governance agents."""
        logger.info("Loading governance agents...")

        # Agent 3: Approval Workflow
        agent = ApprovalWorkflowAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 16: Compliance & Regulatory
        agent = ComplianceRegulatoryAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        logger.info("Governance agents loaded")

    async def _load_portfolio_agents(self):
        """Initialize portfolio management agents."""
        logger.info("Loading portfolio agents...")

        # Agent 4: Demand & Intake
        agent = DemandIntakeAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 5: Business Case & Investment Analysis
        agent = BusinessCaseInvestmentAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 6: Portfolio Strategy & Optimization
        agent = PortfolioStrategyAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 12: Financial Management
        agent = FinancialManagementAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        logger.info("Portfolio agents loaded")

    async def _load_delivery_agents(self):
        """Initialize delivery agents."""
        logger.info("Loading delivery agents...")

        # Agent 7: Program Management
        agent = ProgramManagementAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 8: Project Definition & Scope
        agent = ProjectDefinitionAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 9: Project Lifecycle & Governance
        agent = ProjectLifecycleAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 10: Schedule & Planning
        agent = SchedulePlanningAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 11: Resource & Capacity Management
        agent = ResourceCapacityAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        logger.info("Delivery agents loaded")

    async def _load_operations_agents(self):
        """Initialize operations agents."""
        logger.info("Loading operations agents...")

        # Agent 13: Vendor & Procurement Management
        agent = VendorProcurementAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 14: Quality Management
        agent = QualityManagementAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 15: Risk Management
        agent = RiskManagementAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 17: Change & Configuration Management
        agent = ChangeConfigurationAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 21: Stakeholder & Communications Management
        agent = StakeholderCommunicationsAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        logger.info("Operations agents loaded")

    async def _load_platform_agents(self):
        """Initialize platform agents."""
        logger.info("Loading platform agents...")

        # Agent 18: Release & Deployment
        agent = ReleaseDeploymentAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 19: Knowledge & Document Management
        agent = KnowledgeManagementAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 20: Continuous Improvement & Process Mining
        agent = ProcessMiningAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 22: Analytics & Insights
        agent = AnalyticsInsightsAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 23: Data Synchronization & Consistency
        agent = DataSyncAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 24: Workflow & Process Engine
        agent = WorkflowEngineAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        # Agent 25: System Health & Monitoring
        agent = SystemHealthAgent()
        await agent.initialize()
        self.agents[agent.agent_id] = agent

        logger.info("Platform agents loaded")

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

        # Step 1: Route the query
        intent_result = await self.intent_router.execute({
            "query": query,
            "context": context or {},
        })

        if not intent_result["success"]:
            return {
                "success": False,
                "error": "Failed to route query",
                "details": intent_result,
            }

        # Step 2: Orchestrate response
        orchestration_result = await self.response_orchestrator.execute({
            "routing": intent_result["data"]["routing"],
            "parameters": intent_result["data"]["parameters"],
            "query": query,
        })

        return orchestration_result

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

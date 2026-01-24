"""Platform agents for the Multi-Agent PPM Platform."""

from src.agents.platform.release_deployment.release_deployment_agent import ReleaseDeploymentAgent
from src.agents.platform.knowledge_management.knowledge_management_agent import KnowledgeManagementAgent
from src.agents.platform.process_mining.process_mining_agent import ProcessMiningAgent
from src.agents.platform.analytics_insights.analytics_insights_agent import AnalyticsInsightsAgent
from src.agents.platform.data_sync.data_sync_agent import DataSyncAgent
from src.agents.platform.workflow_engine.workflow_engine_agent import WorkflowEngineAgent
from src.agents.platform.system_health.system_health_agent import SystemHealthAgent

__all__ = [
    "ReleaseDeploymentAgent",
    "KnowledgeManagementAgent",
    "ProcessMiningAgent",
    "AnalyticsInsightsAgent",
    "DataSyncAgent",
    "WorkflowEngineAgent",
    "SystemHealthAgent",
]

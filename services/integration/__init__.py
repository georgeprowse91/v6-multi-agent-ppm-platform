"""Shared integration layer for event bus, analytics, and persistence."""

from services.integration.analytics import AnalyticsClient, AnalyticsSettings
from services.integration.databricks import DatabricksMonteCarloClient, SimulationResult
from services.integration.ai_models import AIModelService, AIModelSettings, ModelTask
from services.integration.event_bus import (
    EventBusClient,
    EventBusSettings,
    EventEnvelope,
    EventType,
)
from services.integration.external_sync import ExternalSyncClient, ExternalSyncSettings
from services.integration.ml import AzureMLClient, AzureMLDurationEstimator, ModelArtifact
from services.integration.persistence import (
    Base,
    CacheClient,
    CacheProvider,
    CacheSettings,
    CosmosSettings,
    ComplianceEvidence,
    PersistenceSettings,
    ProcessLog,
    QualityMetric,
    RiskRecord,
    Schedule,
    ResourceAllocationRecord,
    ScheduleSimulationRecord,
    EarnedValueRecord,
    SqlSettings,
    TaskDependencyRecord,
    TaskRecord,
    create_sql_engine,
    run_migrations,
    SqlRepository,
)

__all__ = [
    "AnalyticsClient",
    "AnalyticsSettings",
    "AIModelService",
    "AIModelSettings",
    "ModelTask",
    "EventBusClient",
    "EventBusSettings",
    "EventEnvelope",
    "EventType",
    "Base",
    "CacheClient",
    "CacheProvider",
    "CacheSettings",
    "CosmosSettings",
    "ComplianceEvidence",
    "DatabricksMonteCarloClient",
    "SimulationResult",
    "ExternalSyncClient",
    "ExternalSyncSettings",
    "AzureMLClient",
    "AzureMLDurationEstimator",
    "ModelArtifact",
    "PersistenceSettings",
    "ProcessLog",
    "QualityMetric",
    "RiskRecord",
    "Schedule",
    "TaskRecord",
    "TaskDependencyRecord",
    "ResourceAllocationRecord",
    "ScheduleSimulationRecord",
    "EarnedValueRecord",
    "SqlSettings",
    "SqlRepository",
    "create_sql_engine",
    "run_migrations",
]

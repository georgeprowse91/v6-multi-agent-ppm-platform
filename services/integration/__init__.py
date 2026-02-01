"""Shared integration layer for event bus, analytics, and persistence."""

from services.integration.analytics import AnalyticsClient, AnalyticsSettings
from services.integration.databricks import DatabricksMonteCarloClient, SimulationResult
from services.integration.event_bus import EventBusClient, EventBusSettings, EventEnvelope
from services.integration.external_sync import ExternalSyncClient, ExternalSyncSettings
from services.integration.ml import AzureMLClient, AzureMLDurationEstimator, ModelArtifact
from services.integration.persistence import (
    Base,
    CacheClient,
    CacheProvider,
    CacheSettings,
    CosmosSettings,
    PersistenceSettings,
    RiskRecord,
    Schedule,
    SqlSettings,
    TaskDependencyRecord,
    TaskRecord,
    create_sql_engine,
    SqlRepository,
)

__all__ = [
    "AnalyticsClient",
    "AnalyticsSettings",
    "EventBusClient",
    "EventBusSettings",
    "EventEnvelope",
    "Base",
    "CacheClient",
    "CacheProvider",
    "CacheSettings",
    "CosmosSettings",
    "DatabricksMonteCarloClient",
    "SimulationResult",
    "ExternalSyncClient",
    "ExternalSyncSettings",
    "AzureMLClient",
    "AzureMLDurationEstimator",
    "ModelArtifact",
    "PersistenceSettings",
    "RiskRecord",
    "Schedule",
    "TaskRecord",
    "TaskDependencyRecord",
    "SqlSettings",
    "SqlRepository",
    "create_sql_engine",
]

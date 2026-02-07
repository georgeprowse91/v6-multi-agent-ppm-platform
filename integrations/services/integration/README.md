# Integration Layer

Shared infrastructure for event bus, analytics, persistence, external connectors, and AI/ML
pipelines. This module is designed to be imported by agents or services across the platform.

## Configuration

All configuration uses environment variables with sensible defaults. Each module uses a
pydantic settings object and supports loading from `.env`.

| Area | Settings class | Environment prefix | Examples |
| --- | --- | --- | --- |
| Event Bus | `EventBusSettings` | `EVENT_BUS_` | `EVENT_BUS_PROVIDER=service_bus` |
| Analytics | `AnalyticsSettings` | `ANALYTICS_` | `ANALYTICS_PROVIDER=azure_monitor` |
| Persistence | `PersistenceSettings` | `PERSISTENCE_` | `PERSISTENCE_SQL_CONNECTION_STRING=...` |
| AI Models | `AIModelSettings` | `AI_MODEL_` | `AI_MODEL_PROVIDER=in_memory` |
| Connectors | `ConnectorSettings` | `CONNECTOR_` | `CONNECTOR_TIMEOUT_SECONDS=15` |

## Event Bus

```python
from services.integration.event_bus import EventBusClient, EventEnvelope, EventType

bus = EventBusClient()

bus.create_topic("ppm-events")

bus.publish_event(
    EventEnvelope(
        event_type=EventType.SCHEDULE_CREATED,
        subject="schedule/123",
        data={"schedule_id": 123, "owner": "portfolio"},
    )
)
```

Kafka settings:

```bash
EVENT_BUS_PROVIDER=kafka
EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=broker:9092
EVENT_BUS_KAFKA_TOPIC=ppm-events
```

## Analytics

```python
from services.integration.analytics import AnalyticsClient

analytics = AnalyticsClient()
analytics.record_event("deployment.completed", {"service": "planner"})
analytics.record_metric("deployment.duration", 42.0)
analytics.record_kpi("portfolio.throughput", 18)
analytics.record_defect_rate("planner.defects", 0.02)
analytics.record_deployment_metric("planner.deployments", 3)
```

## Persistence

```python
from services.integration.persistence import Base, SqlRepository, create_sql_engine
from sqlalchemy.orm import Session

engine = create_sql_engine("sqlite+pysqlite:///:memory:")
Base.metadata.create_all(engine)

with Session(engine) as session:
    repo = SqlRepository(session)
    repo.add_risk("Data quality", "high", "Add validation")
    repo.add_compliance_evidence("audit_log", "evidence/123", "collected", "signed")
```

## External Connector Framework

```python
from connectors.integration import (
    ConnectorRegistry,
    IntegrationAuthType,
    IntegrationConfig,
    JiraConnector,
)

registry = ConnectorRegistry()
registry.register(JiraConnector.system_name, JiraConnector)

config = IntegrationConfig(
    system="jira",
    base_url="https://your-domain.atlassian.net",
    auth_type=IntegrationAuthType.API_KEY,
    api_key="token",
)
connector = registry.create("jira", config)
connector.authenticate()
```

## AI/ML Models

```python
from services.integration.ai_models import AIModelService, ModelTask

service = AIModelService()
result = service.train_model(ModelTask.SCHEDULE_ESTIMATION, [3.0, 5.0, 4.5])
service.evaluate_model(result.record.model_id, [4.0, 6.0])
service.deploy_model(result.record.model_id)
prediction = service.predict(result.record.model_id, {"weight": 1.2, "complexity": 1.1})
```

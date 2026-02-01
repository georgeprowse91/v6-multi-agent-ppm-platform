# Integration Layer

Shared infrastructure for event bus, analytics, and persistence. This module is designed to be
imported by agents or services across the platform.

## Configuration

All configuration uses environment variables with sensible defaults. Each module uses a
pydantic settings object and supports loading from `.env`.

| Area | Settings class | Environment prefix | Examples |
| --- | --- | --- | --- |
| Event Bus | `EventBusSettings` | `EVENT_BUS_` | `EVENT_BUS_PROVIDER=service_bus` |
| Analytics | `AnalyticsSettings` | `ANALYTICS_` | `ANALYTICS_PROVIDER=azure_monitor` |
| Persistence | `PersistenceSettings` | `PERSISTENCE_` | `PERSISTENCE_SQL_CONNECTION_STRING=...` |

## Event Bus

```python
from services.integration.event_bus import EventBusClient, EventEnvelope

bus = EventBusClient()

bus.create_topic("ppm-events")

bus.publish_event(
    EventEnvelope(
        event_type="schedule.created",
        subject="schedule/123",
        data={"schedule_id": 123, "owner": "portfolio"},
    )
)
```

## Analytics

```python
from services.integration.analytics import AnalyticsClient

analytics = AnalyticsClient()
analytics.record_event("deployment.completed", {"service": "planner"})
analytics.record_metric("deployment.duration", 42.0)
analytics.record_error_rate("planner.errors", 0.02)
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
```

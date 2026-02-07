"""Example usage for the shared integration layer."""

from sqlalchemy.orm import Session

from integrations.services.integration.analytics import AnalyticsClient
from integrations.services.integration.event_bus import EventBusClient, EventEnvelope
from integrations.services.integration.persistence import Base, SqlRepository, create_sql_engine


def main() -> None:
    bus = EventBusClient()
    bus.publish_event(
        EventEnvelope(
            event_type="schedule.created",
            subject="schedule/42",
            data={"schedule_id": 42, "owner": "portfolio"},
        )
    )

    engine = create_sql_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repo = SqlRepository(session)
        repo.add_risk("Integration risk", "medium", "Align dependencies")

    analytics = AnalyticsClient()
    analytics.record_metric("deployment.duration", 36.5, {"service": "planner"})


if __name__ == "__main__":
    main()

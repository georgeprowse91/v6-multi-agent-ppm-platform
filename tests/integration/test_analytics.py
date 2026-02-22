from integrations.services.integration.analytics import (
    AnalyticsClient,
    AnalyticsSettings,
    InMemoryAnalyticsProvider,
)


def test_record_event_and_metric():
    provider = InMemoryAnalyticsProvider()
    settings = AnalyticsSettings(provider="in_memory")
    client = AnalyticsClient(settings=settings, provider=provider)

    client.record_event("deployment.completed", {"service": "planner"})
    client.record_metric("deployment.duration", 12.3)
    client.record_error_rate("planner.errors", 0.05)
    client.record_kpi("portfolio.throughput", 20.0)
    client.record_defect_rate("planner.defects", 0.01)
    client.record_deployment_metric("planner.deployments", 3.0)

    assert len(provider.records) == 6
    assert provider.records[0].name == "deployment.completed"
    assert provider.records[1].value == 12.3


def test_detect_anomaly():
    client = AnalyticsClient(settings=AnalyticsSettings(provider="in_memory"))
    series = [1.0, 1.1, 0.9, 1.0, 5.0]
    assert client.detect_anomaly(series, threshold=1.5) is True


def test_list_records_filters():
    provider = InMemoryAnalyticsProvider()
    client = AnalyticsClient(settings=AnalyticsSettings(provider="in_memory"), provider=provider)
    client.record_metric("service.latency", 100.0)
    client.record_error_rate("service.errors", 0.05)

    records = client.list_records(category="error_rate")

    assert len(records) == 1
    assert records[0].name == "service.errors"

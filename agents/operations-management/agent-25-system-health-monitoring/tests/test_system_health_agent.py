import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
if OBSERVABILITY_ROOT.exists() and str(OBSERVABILITY_ROOT) not in sys.path:
    sys.path.insert(0, str(OBSERVABILITY_ROOT))

import pytest

from integrations.services.integration.analytics import (
    AnalyticsClient,
    AnalyticsSettings,
    InMemoryAnalyticsProvider,
)

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "agent-25-system-health-agent"
    / "src"
    / "system_health_agent.py"
)
spec = importlib.util.spec_from_file_location("system_health_agent", MODULE_PATH)
health_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(health_module)

SystemHealthAgent = health_module.SystemHealthAgent


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


def test_parse_prometheus_metrics() -> None:
    agent = SystemHealthAgent(config={})
    payload = """
# HELP node_cpu_seconds_total Seconds the CPUs spent in each mode.
node_cpu_seconds_total{cpu=\"0\",mode=\"idle\"} 100
node_cpu_seconds_total{cpu=\"0\",mode=\"user\"} 50
node_cpu_seconds_total{cpu=\"1\",mode=\"idle\"} 120
node_cpu_seconds_total{cpu=\"1\",mode=\"user\"} 60
node_memory_MemTotal_bytes 1000
node_memory_MemAvailable_bytes 200
node_filesystem_size_bytes{mountpoint=\"/\",fstype=\"ext4\"} 1000
node_filesystem_avail_bytes{mountpoint=\"/\",fstype=\"ext4\"} 100
node_network_receive_bytes_total{device=\"eth0\"} 1000
node_network_transmit_bytes_total{device=\"eth0\"} 500
"""
    metrics = agent._parse_prometheus_metrics(payload)
    assert metrics["cpu_usage"] == pytest.approx(0.333, rel=1e-2)
    assert metrics["memory_usage"] == pytest.approx(0.8, rel=1e-3)
    assert metrics["disk_usage"] == pytest.approx(0.9, rel=1e-3)
    assert metrics["network_rx_bytes_total"] == 1000
    assert metrics["network_tx_bytes_total"] == 500


@pytest.mark.anyio
async def test_collect_application_metrics(tmp_path) -> None:
    provider = InMemoryAnalyticsProvider()
    analytics_client = AnalyticsClient(
        settings=AnalyticsSettings(provider="in_memory"), provider=provider
    )
    analytics_client.record_metric("api.latency", 120.0, {"service_name": "api"})
    analytics_client.record_error_rate("api.errors", 0.05, {"service_name": "api"})

    agent = SystemHealthAgent(
        config={
            "analytics_client": analytics_client,
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )

    response = await agent._collect_application_metrics("tenant-a", {"hours": 1})
    assert response["services"]["api"]["request_latency_ms"] == pytest.approx(120.0)
    assert response["services"]["api"]["error_rate"] == pytest.approx(0.05)


@pytest.mark.anyio
async def test_anomaly_detection_detects_outlier() -> None:
    agent = SystemHealthAgent(config={})
    metrics = [
        {"metrics": {"error_rate": 0.01}, "timestamp": "2024-01-01T00:00:00"},
        {"metrics": {"error_rate": 0.02}, "timestamp": "2024-01-01T00:01:00"},
        {"metrics": {"error_rate": 0.015}, "timestamp": "2024-01-01T00:02:00"},
        {"metrics": {"error_rate": 0.018}, "timestamp": "2024-01-01T00:02:30"},
        {"metrics": {"error_rate": 0.9}, "timestamp": "2024-01-01T00:03:00"},
    ]
    anomalies = await agent._apply_anomaly_detection(metrics)
    assert any(anomaly["metric"] == "error_rate" for anomaly in anomalies)


@pytest.mark.anyio
async def test_collect_metrics_triggers_alert(tmp_path) -> None:
    agent = SystemHealthAgent(
        config={
            "alert_threshold_error_rate": 0.01,
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    response = await agent._collect_metrics(
        "tenant-a",
        "api",
        {"error_rate": 0.2, "response_time_ms": 250},
    )
    assert response["alerts_triggered"]
    assert agent.alerts


@pytest.mark.anyio
async def test_health_status_events_are_published(tmp_path) -> None:
    event_bus = DummyEventBus()
    agent = SystemHealthAgent(
        config={
            "event_bus": event_bus,
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    await agent._publish_health_status({"api": {"healthy": True}})
    await agent._publish_health_status({"api": {"healthy": False}})
    topics = [topic for topic, _ in event_bus.published]
    assert "system.health.ok" in topics
    assert "system.health.alert" in topics
    assert "system.health.updated" in topics


@pytest.mark.anyio
async def test_environment_health_blocks_on_critical_alert(tmp_path) -> None:
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    await agent._create_alert(
        "tenant-a",
        {
            "name": "API error rate spike",
            "description": "error rate exceeded",
            "severity": "critical",
            "service_name": "api",
            "condition": "error_rate",
            "threshold": 0.05,
        },
    )
    health = await agent._get_environment_health("production")
    assert health["block_deployment"] is True


@pytest.mark.anyio
async def test_grafana_dashboard_payload() -> None:
    agent = SystemHealthAgent(config={})
    payload = await agent._get_grafana_dashboard()
    assert payload["dashboard"]["title"] == "System Health Overview"


@pytest.mark.anyio
async def test_reporting_summaries(tmp_path) -> None:
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    alert = await agent._create_alert(
        "tenant-a",
        {
            "name": "API error rate spike",
            "description": "error rate exceeded",
            "severity": "critical",
            "service_name": "api",
            "condition": "error_rate",
            "threshold": 0.05,
        },
    )
    assert alert["alert_id"]

    incident = await agent._create_incident(
        "tenant-a",
        {
            "title": "API outage",
            "description": "service down",
            "severity": "critical",
            "affected_services": ["api"],
        },
    )
    assert incident["incident_id"]

    dashboard = await agent._get_health_dashboard("tenant-a", {"hours": 1})
    assert dashboard["alert_summary"]["total_alerts"] == 1
    assert dashboard["incident_summary"]["total_incidents"] == 1

    report = await agent._get_postmortem_report("tenant-a", {"hours": 1})
    assert report["alert_summary"]["total_alerts"] == 1
    assert report["incident_summary"]["total_incidents"] == 1

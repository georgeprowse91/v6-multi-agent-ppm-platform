"""Tests for the RegulatoryComplianceConnector."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "connectors" / "sdk" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "connectors" / "regulatory_compliance" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "packages" / "common" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "vendor" / "stubs"))
sys.path.insert(0, str(_REPO_ROOT / "vendor"))
sys.path.insert(0, str(_REPO_ROOT))

from base_connector import (
    ConnectionStatus,
    ConnectorCategory,
    ConnectorConfig,
    SyncDirection,
    SyncFrequency,
)
from regulatory_compliance_connector import (
    RegulatoryComplianceConnector,
    create_regulatory_compliance_connector,
)


def _make_config(**overrides: Any) -> ConnectorConfig:
    defaults = {
        "connector_id": "regulatory_compliance",
        "name": "Regulatory Compliance",
        "category": ConnectorCategory.COMPLIANCE,
        "enabled": True,
        "sync_direction": SyncDirection.INBOUND,
        "sync_frequency": SyncFrequency.DAILY,
        "instance_url": "https://compliance.example.com",
    }
    defaults.update(overrides)
    return ConnectorConfig(**defaults)


def _make_response(status_code: int = 200, json_data: Any = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    return response


class TestRegulatoryComplianceConnector:
    def test_connector_metadata(self) -> None:
        config = _make_config()
        connector = RegulatoryComplianceConnector(config)
        assert connector.CONNECTOR_ID == "regulatory_compliance"
        assert connector.CONNECTOR_NAME == "Regulatory Compliance"
        assert connector.CONNECTOR_VERSION == "1.0.0"
        assert connector.CONNECTOR_CATEGORY == ConnectorCategory.COMPLIANCE
        assert connector.SUPPORTS_WRITE is True

    @patch.dict(os.environ, {
        "REGULATORY_COMPLIANCE_ENDPOINT": "https://compliance.example.com",
        "REGULATORY_COMPLIANCE_API_KEY": "test-key-123",
    })
    def test_authenticate_success(self) -> None:
        mock_client = MagicMock()
        mock_client.request.return_value = _make_response(200)
        config = _make_config()
        connector = RegulatoryComplianceConnector(config, client=mock_client)
        assert connector.authenticate() is True

    @patch.dict(os.environ, {
        "REGULATORY_COMPLIANCE_ENDPOINT": "https://compliance.example.com",
        "REGULATORY_COMPLIANCE_API_KEY": "bad-key",
    })
    def test_authenticate_failure(self) -> None:
        mock_client = MagicMock()
        mock_client.request.return_value = _make_response(401)
        config = _make_config()
        connector = RegulatoryComplianceConnector(config, client=mock_client)
        assert connector.authenticate() is False

    @patch.dict(os.environ, {
        "REGULATORY_COMPLIANCE_ENDPOINT": "https://compliance.example.com",
        "REGULATORY_COMPLIANCE_API_KEY": "test-key-123",
    })
    def test_test_connection_success(self) -> None:
        mock_client = MagicMock()
        mock_client.request.return_value = _make_response(200)
        config = _make_config()
        connector = RegulatoryComplianceConnector(config, client=mock_client)
        result = connector.test_connection()
        assert result.status == ConnectionStatus.CONNECTED

    @patch.dict(os.environ, {
        "REGULATORY_COMPLIANCE_ENDPOINT": "https://compliance.example.com",
        "REGULATORY_COMPLIANCE_API_KEY": "test-key-123",
    })
    def test_read_audit_logs(self) -> None:
        mock_client = MagicMock()
        health_response = _make_response(200)
        read_response = _make_response(200, {
            "items": [
                {
                    "id": "log-001",
                    "event_type": "access",
                    "actor": "user@example.com",
                    "action": "view",
                    "resource": "patient_record",
                    "timestamp": "2026-03-01T10:00:00Z",
                    "regulation": "HIPAA",
                    "compliance_status": "compliant",
                },
            ]
        })
        mock_client.request.side_effect = [health_response, read_response]
        config = _make_config()
        connector = RegulatoryComplianceConnector(config, client=mock_client)
        records = connector.read("audit_logs")
        assert len(records) == 1
        assert records[0]["id"] == "log-001"

    @patch.dict(os.environ, {
        "REGULATORY_COMPLIANCE_ENDPOINT": "https://compliance.example.com",
        "REGULATORY_COMPLIANCE_API_KEY": "test-key-123",
    })
    def test_read_unsupported_resource(self) -> None:
        mock_client = MagicMock()
        mock_client.request.return_value = _make_response(200)
        config = _make_config()
        connector = RegulatoryComplianceConnector(config, client=mock_client)
        connector.authenticate()
        with pytest.raises(ValueError, match="Unsupported resource type"):
            connector.read("nonexistent")

    @patch.dict(os.environ, {
        "REGULATORY_COMPLIANCE_ENDPOINT": "https://compliance.example.com",
        "REGULATORY_COMPLIANCE_API_KEY": "test-key-123",
    })
    def test_write_audit_logs(self) -> None:
        mock_client = MagicMock()
        health_response = _make_response(200)
        write_response = _make_response(200, {
            "items": [{"id": "log-new", "status": "created"}]
        })
        mock_client.request.side_effect = [health_response, write_response]
        config = _make_config()
        connector = RegulatoryComplianceConnector(config, client=mock_client)
        data = [{"event_type": "modification", "actor": "admin@example.com"}]
        results = connector.write("audit_logs", data)
        assert len(results) == 1

    def test_get_schema(self) -> None:
        config = _make_config()
        connector = RegulatoryComplianceConnector(config)
        schema = connector.get_schema()
        assert "audit_logs" in schema
        assert "compliance_events" in schema
        assert "regulations" in schema
        assert "findings" in schema

    def test_factory_function(self) -> None:
        connector = create_regulatory_compliance_connector(
            endpoint_url="https://compliance.example.com",
            sync_direction="inbound",
        )
        assert isinstance(connector, RegulatoryComplianceConnector)
        assert connector.config.instance_url == "https://compliance.example.com"

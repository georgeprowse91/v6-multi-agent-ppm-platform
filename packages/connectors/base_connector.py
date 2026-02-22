"""Connector resilience base abstractions.

This module exposes the standard :class:`BaseConnector` used by connector
implementations across the platform.
"""

from integrations.connectors.sdk.src.base_connector import (  # noqa: F401
    BaseConnector,
    CircuitBreakerOpenError,
    ConnectorCallFailedError,
    ConnectorError,
    ConnectorSchemaValidationError,
)

__all__ = [
    "BaseConnector",
    "CircuitBreakerOpenError",
    "ConnectorCallFailedError",
    "ConnectorError",
    "ConnectorSchemaValidationError",
]

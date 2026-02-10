"""Shared connector abstractions package."""

from .base_connector import (
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

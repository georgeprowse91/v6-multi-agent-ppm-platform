"""Centralized exception hierarchy for the PPM platform."""

from __future__ import annotations

from typing import Any


class PPMPlatformError(Exception):
    """Base class for all PPM platform errors."""

    status_code = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(PPMPlatformError):
    """Raised when request validation fails."""

    status_code = 400


class AuthenticationError(PPMPlatformError):
    """Raised when authentication fails."""

    status_code = 401


class AuthorizationError(PPMPlatformError):
    """Raised when authorization fails."""

    status_code = 403


class ResourceNotFoundError(PPMPlatformError):
    """Raised when a requested resource is not found."""

    status_code = 404


class ConflictError(PPMPlatformError):
    """Raised when a request conflicts with the current state of a resource."""

    status_code = 409


class ExternalServiceError(PPMPlatformError):
    """Raised when an external dependency fails."""

    status_code = 502


class ServiceUnavailableError(PPMPlatformError):
    """Raised when a service is temporarily unavailable."""

    status_code = 503


class RateLimitExceededError(PPMPlatformError):
    """Raised when rate limits are exceeded."""

    status_code = 429


class WorkflowError(PPMPlatformError):
    """Raised when workflow execution fails."""

    status_code = 500


class AgentError(PPMPlatformError):
    """Raised when agent execution fails."""

    status_code = 500


class ConnectorError(PPMPlatformError):
    """Raised when connector operations fail."""

    status_code = 500


EXCEPTION_STATUS_MAP: dict[type[PPMPlatformError], int] = {
    ValidationError: ValidationError.status_code,
    AuthenticationError: AuthenticationError.status_code,
    AuthorizationError: AuthorizationError.status_code,
    ResourceNotFoundError: ResourceNotFoundError.status_code,
    ConflictError: ConflictError.status_code,
    ExternalServiceError: ExternalServiceError.status_code,
    ServiceUnavailableError: ServiceUnavailableError.status_code,
    RateLimitExceededError: RateLimitExceededError.status_code,
    WorkflowError: WorkflowError.status_code,
    AgentError: AgentError.status_code,
    ConnectorError: ConnectorError.status_code,
}


def exception_to_http_status(exc: Exception) -> int:
    """Map platform exceptions to HTTP status codes.

    Resolves the status code from the exception's class attribute, falling
    back to the static map for backwards compatibility with any subclass
    that does not define ``status_code`` directly.
    """
    if isinstance(exc, PPMPlatformError):
        return getattr(exc, "status_code", PPMPlatformError.status_code)

    for exc_type, status_code in EXCEPTION_STATUS_MAP.items():
        if isinstance(exc, exc_type):
            return status_code

    return 500

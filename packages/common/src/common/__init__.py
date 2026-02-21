"""Common shared utilities for the PPM platform."""

from .exceptions import (  # noqa: F401
    AgentError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    ConnectorError,
    ExternalServiceError,
    PPMPlatformError,
    RateLimitExceededError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
    WorkflowError,
    exception_to_http_status,
)
try:
    from .resilience import (  # noqa: F401
        CircuitOpenError,
        CircuitBreakerPolicy,
        DependencyResilienceConfig,
        ResilienceMiddleware,
        RetryPolicy,
        TimeoutPolicy,
        dependency_config_from_env,
    )
except ModuleNotFoundError:  # pragma: no cover - optional runtime deps in isolated contexts
    CircuitOpenError = None  # type: ignore[assignment]
    CircuitBreakerPolicy = None  # type: ignore[assignment]
    DependencyResilienceConfig = None  # type: ignore[assignment]
    ResilienceMiddleware = None  # type: ignore[assignment]
    RetryPolicy = None  # type: ignore[assignment]
    TimeoutPolicy = None  # type: ignore[assignment]
    dependency_config_from_env = None  # type: ignore[assignment]

__all__ = [
    "AgentError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "ConnectorError",
    "ExternalServiceError",
    "PPMPlatformError",
    "RateLimitExceededError",
    "ResourceNotFoundError",
    "ServiceUnavailableError",
    "ValidationError",
    "WorkflowError",
    "exception_to_http_status",
    "CircuitOpenError",
    "CircuitBreakerPolicy",
    "DependencyResilienceConfig",
    "ResilienceMiddleware",
    "RetryPolicy",
    "TimeoutPolicy",
    "dependency_config_from_env",
]

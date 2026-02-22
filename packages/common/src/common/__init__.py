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
        CircuitBreakerPolicy,
        CircuitOpenError,
        DependencyResilienceConfig,
        ResilienceMiddleware,
        RetryPolicy,
        TimeoutPolicy,
        dependency_config_from_env,
    )
except ModuleNotFoundError:  # pragma: no cover - optional runtime deps in isolated contexts
    CircuitOpenError = None  # type: ignore[assignment, misc]
    CircuitBreakerPolicy = None  # type: ignore[assignment, misc]
    DependencyResilienceConfig = None  # type: ignore[assignment, misc]
    ResilienceMiddleware = None  # type: ignore[assignment, misc]
    RetryPolicy = None  # type: ignore[assignment, misc]
    TimeoutPolicy = None  # type: ignore[assignment, misc]
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

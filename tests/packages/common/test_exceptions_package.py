from __future__ import annotations

import pytest

from common.exceptions import (
    EXCEPTION_STATUS_MAP,
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


@pytest.mark.parametrize(
    ("exc_type", "expected_status"),
    [
        (ValidationError, 400),
        (AuthenticationError, 401),
        (AuthorizationError, 403),
        (ResourceNotFoundError, 404),
        (ConflictError, 409),
        (RateLimitExceededError, 429),
        (ExternalServiceError, 502),
        (ServiceUnavailableError, 503),
        (WorkflowError, 500),
        (AgentError, 500),
        (ConnectorError, 500),
    ],
)
def test_exception_hierarchy_and_status_map_invariants(exc_type: type[PPMPlatformError], expected_status: int) -> None:
    assert issubclass(exc_type, PPMPlatformError)
    assert exc_type.status_code == expected_status
    assert EXCEPTION_STATUS_MAP[exc_type] == expected_status


def test_every_custom_exception_is_mapped() -> None:
    mapped_types = set(EXCEPTION_STATUS_MAP)
    for exc_type in PPMPlatformError.__subclasses__():
        assert exc_type in mapped_types


@pytest.mark.parametrize("exc_type", list(EXCEPTION_STATUS_MAP))
def test_exception_to_http_status_uses_exception_type_status(exc_type: type[PPMPlatformError]) -> None:
    exc = exc_type("failure")
    assert exception_to_http_status(exc) == exc_type.status_code


def test_exception_to_http_status_unknown_exception_defaults_to_500() -> None:
    assert exception_to_http_status(RuntimeError("unexpected")) == 500


def test_exception_serialization_and_message_formatting_consistency() -> None:
    details = {"field": "name", "reason": "required"}
    exc = ValidationError("Invalid payload", details=details)

    payload = {
        "error": exc.__class__.__name__,
        "message": exc.message,
        "details": exc.details,
        "status": exception_to_http_status(exc),
    }

    assert str(exc) == "Invalid payload"
    assert payload == {
        "error": "ValidationError",
        "message": "Invalid payload",
        "details": details,
        "status": 400,
    }


def test_exception_default_details_is_empty_dict() -> None:
    exc = ConnectorError("connector failed")
    assert exc.details == {}

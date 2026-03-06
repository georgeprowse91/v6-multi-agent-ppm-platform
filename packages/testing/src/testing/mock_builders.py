"""Factory functions for building test data objects.

Each builder returns a dictionary matching the corresponding canonical
JSON schema in ``data/schemas/``, with sensible defaults that can be
overridden via keyword arguments.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


def build_project(**overrides: Any) -> dict[str, Any]:
    """Build a sample project entity.

    All fields can be overridden via keyword arguments.
    """
    base: dict[str, Any] = {
        "id": _uuid(),
        "name": "Test Project",
        "status": "active",
        "methodology": "adaptive",
        "portfolio_id": _uuid(),
        "created_at": _utcnow_iso(),
        "updated_at": _utcnow_iso(),
    }
    base.update(overrides)
    return base


def build_risk(**overrides: Any) -> dict[str, Any]:
    """Build a sample risk entity."""
    base: dict[str, Any] = {
        "id": _uuid(),
        "project_id": _uuid(),
        "title": "Test Risk",
        "description": "A test risk for unit testing.",
        "probability": 0.3,
        "impact": 0.7,
        "severity": "high",
        "status": "open",
        "mitigation_strategy": "Mitigate through testing.",
        "created_at": _utcnow_iso(),
    }
    base.update(overrides)
    return base


def build_demand(**overrides: Any) -> dict[str, Any]:
    """Build a sample demand intake entity."""
    base: dict[str, Any] = {
        "id": _uuid(),
        "title": "Test Demand",
        "description": "A test demand request.",
        "requester": "test_user",
        "priority": "medium",
        "status": "submitted",
        "created_at": _utcnow_iso(),
    }
    base.update(overrides)
    return base


def build_agent_run(**overrides: Any) -> dict[str, Any]:
    """Build a sample agent-run record."""
    base: dict[str, Any] = {
        "id": _uuid(),
        "agent_id": "risk-management",
        "session_id": _uuid(),
        "status": "completed",
        "input": {"query": "Assess project risks"},
        "output": {"risks_identified": 3},
        "started_at": _utcnow_iso(),
        "completed_at": _utcnow_iso(),
        "duration_ms": 1250,
    }
    base.update(overrides)
    return base


def build_auth_headers(
    *,
    user_id: str = "user-123",
    roles: list[str] | None = None,
    tenant_id: str = "tenant-alpha",
    secret: str = "test-secret",
) -> dict[str, str]:
    """Build JWT authorization headers for test requests.

    Requires ``PyJWT`` to be installed.  Skips gracefully in environments
    where the ``cryptography`` backend is unavailable.

    Args:
        user_id: Subject claim.
        roles: List of role strings.
        tenant_id: Tenant identifier.
        secret: JWT signing secret.

    Returns:
        A dictionary with ``Authorization`` and ``X-Tenant-ID`` headers.
    """
    try:
        import jwt
    except Exception as exc:
        raise RuntimeError(
            "PyJWT is required to build auth headers. Install with: pip install PyJWT"
        ) from exc

    if roles is None:
        roles = ["portfolio_admin"]

    token = jwt.encode(
        {
            "sub": user_id,
            "roles": roles,
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": tenant_id,
        },
        secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

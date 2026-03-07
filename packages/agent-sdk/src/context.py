"""Agent execution context provided to custom agents at runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """Runtime context injected into custom agent executions.

    Provides tenant-scoped access to platform services without
    exposing internal implementation details.
    """

    tenant_id: str
    correlation_id: str
    user_id: str | None = None
    user_roles: list[str] = field(default_factory=list)
    project_id: str | None = None
    environment: str = "production"
    feature_flags: dict[str, bool] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: str) -> bool:
        """Check if the executing user has a given permission.

        Note: This is a convenience check against the context roles.
        The actual policy enforcement happens at the platform level.
        """
        # Admins always have access
        if "PMO_ADMIN" in self.user_roles or "tenant_owner" in self.user_roles:
            return True
        # For non-admin roles, rely on platform-level enforcement
        return False

    def is_feature_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled in the current context."""
        return self.feature_flags.get(flag_name, False)

    @classmethod
    def from_input_data(cls, input_data: dict[str, Any]) -> AgentContext:
        """Build an AgentContext from the standard agent input_data dict."""
        context = input_data.get("context", {})
        return cls(
            tenant_id=context.get("tenant_id", input_data.get("tenant_id", "unknown")),
            correlation_id=context.get("correlation_id", input_data.get("correlation_id", "")),
            user_id=context.get("user_id"),
            user_roles=context.get("user_roles", []),
            project_id=context.get("project_id", input_data.get("project_id")),
            environment=context.get("environment", "production"),
            feature_flags=context.get("feature_flags", {}),
            extra={k: v for k, v in context.items() if k not in {
                "tenant_id", "correlation_id", "user_id", "user_roles",
                "project_id", "environment", "feature_flags",
            }},
        )

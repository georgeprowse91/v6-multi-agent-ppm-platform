"""
Policy Package

Provides lightweight RBAC/ABAC policy evaluation utilities used across
platform services and agents.  Policies are composed of named rules
that map (subject, action, resource) triples to an ALLOW or DENY effect.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class Effect(StrEnum):
    """Policy decision effect."""

    ALLOW = "allow"
    DENY = "deny"


@dataclass
class PolicyContext:
    """Runtime context supplied to a policy rule for evaluation."""

    subject: str
    """Identity performing the action (user ID, service account, etc.)."""

    action: str
    """The operation being attempted (e.g. 'agents:update', 'projects:create')."""

    resource: str
    """The resource being acted upon (e.g. 'agent-01-intent-router', '*')."""

    roles: list[str] = field(default_factory=list)
    """Roles assigned to the subject."""

    tenant_id: str | None = None
    """Tenant scope for multi-tenant evaluation."""

    attributes: dict[str, Any] = field(default_factory=dict)
    """Additional ABAC attributes (e.g. project_id, classification, environment)."""


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""

    effect: Effect
    policy_id: str
    rule_id: str
    reason: str = ""

    @property
    def allowed(self) -> bool:
        return self.effect == Effect.ALLOW

    def to_dict(self) -> dict[str, Any]:
        return {
            "effect": self.effect.value,
            "policy_id": self.policy_id,
            "rule_id": self.rule_id,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Rule types
# ---------------------------------------------------------------------------

ConditionFn = Callable[[PolicyContext], bool]


@dataclass
class PolicyRule:
    """
    A single rule within a policy.

    Rules are evaluated in sequence order (ascending).  The first matching
    rule short-circuits evaluation for that policy.

    Attributes:
        rule_id: Unique identifier for the rule.
        description: Human-readable description.
        effect: ALLOW or DENY.
        actions: Glob-style patterns for actions this rule applies to.
        resources: Glob-style patterns for resources this rule applies to.
        roles: If non-empty, at least one of these roles must be present on
               the subject for the rule to match.
        condition: Optional callable for attribute-based conditions.
        sequence: Evaluation order (lower numbers evaluated first).
    """

    rule_id: str
    description: str
    effect: Effect
    actions: list[str] = field(default_factory=lambda: ["*"])
    resources: list[str] = field(default_factory=lambda: ["*"])
    roles: list[str] = field(default_factory=list)
    condition: ConditionFn | None = field(default=None, compare=False, repr=False)
    sequence: int = 100

    def matches(self, ctx: PolicyContext) -> bool:
        """Return True if this rule applies to the given context."""
        if not any(_glob_match(pattern, ctx.action) for pattern in self.actions):
            return False
        if not any(_glob_match(pattern, ctx.resource) for pattern in self.resources):
            return False
        if self.roles and not any(role in ctx.roles for role in self.roles):
            return False
        if self.condition is not None:
            try:
                return self.condition(ctx)
            except Exception as exc:
                logger.warning("Policy rule condition raised an exception: %s", exc)
                return False
        return True


def _glob_match(pattern: str, value: str) -> bool:
    """Lightweight glob matching supporting '*' and '?' wildcards."""
    if pattern == "*":
        return True
    regex = "^" + re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".") + "$"
    return bool(re.match(regex, value))


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


@dataclass
class Policy:
    """
    A named collection of ordered rules.

    Evaluation returns the effect of the first matching rule.
    If no rule matches the default effect is DENY.
    """

    policy_id: str
    name: str
    description: str = ""
    rules: list[PolicyRule] = field(default_factory=list)
    default_effect: Effect = Effect.DENY

    def evaluate(self, ctx: PolicyContext) -> PolicyDecision:
        """Evaluate the policy against the given context."""
        for rule in sorted(self.rules, key=lambda r: r.sequence):
            if rule.matches(ctx):
                return PolicyDecision(
                    effect=rule.effect,
                    policy_id=self.policy_id,
                    rule_id=rule.rule_id,
                    reason=rule.description,
                )
        return PolicyDecision(
            effect=self.default_effect,
            policy_id=self.policy_id,
            rule_id="__default__",
            reason="No matching rule; default effect applied.",
        )

    def add_rule(self, rule: PolicyRule) -> None:
        self.rules.append(rule)


# ---------------------------------------------------------------------------
# Built-in platform policies
# ---------------------------------------------------------------------------

_AGENT_CONFIG_POLICY = Policy(
    policy_id="ppm.agent-config",
    name="Agent Configuration Access",
    description="Controls who can read and modify agent configurations.",
    rules=[
        PolicyRule(
            rule_id="deny-non-tenant",
            description="Deny access when tenant_id is missing.",
            effect=Effect.DENY,
            actions=["*"],
            resources=["*"],
            condition=lambda ctx: ctx.tenant_id is None,
            sequence=1,
        ),
        PolicyRule(
            rule_id="allow-pmo-admin-write",
            description="PMO_ADMIN may perform any action on agent configs.",
            effect=Effect.ALLOW,
            actions=["agents:*"],
            resources=["*"],
            roles=["PMO_ADMIN"],
            sequence=10,
        ),
        PolicyRule(
            rule_id="allow-pm-read",
            description="PM role may read agent configs.",
            effect=Effect.ALLOW,
            actions=["agents:read", "agents:list"],
            resources=["*"],
            roles=["PM", "TEAM_MEMBER", "AUDITOR"],
            sequence=20,
        ),
        PolicyRule(
            rule_id="allow-pm-patch",
            description="PM role may update agent parameters.",
            effect=Effect.ALLOW,
            actions=["agents:update"],
            resources=["*"],
            roles=["PM"],
            sequence=25,
        ),
    ],
)

_PROJECT_ACCESS_POLICY = Policy(
    policy_id="ppm.project-access",
    name="Project Resource Access",
    description="Controls access to project-scoped resources.",
    rules=[
        PolicyRule(
            rule_id="allow-pmo-admin-all",
            description="PMO_ADMIN has full access to all projects.",
            effect=Effect.ALLOW,
            actions=["projects:*"],
            resources=["*"],
            roles=["PMO_ADMIN"],
            sequence=10,
        ),
        PolicyRule(
            rule_id="allow-pm-own-project",
            description="PM can manage their own project resources.",
            effect=Effect.ALLOW,
            actions=["projects:read", "projects:update", "projects:create"],
            resources=["*"],
            roles=["PM"],
            sequence=20,
        ),
        PolicyRule(
            rule_id="allow-team-member-read",
            description="TEAM_MEMBER can read project data.",
            effect=Effect.ALLOW,
            actions=["projects:read"],
            resources=["*"],
            roles=["TEAM_MEMBER", "COLLABORATOR"],
            sequence=30,
        ),
        PolicyRule(
            rule_id="allow-auditor-read",
            description="AUDITOR can read all project resources.",
            effect=Effect.ALLOW,
            actions=["projects:read", "projects:list"],
            resources=["*"],
            roles=["AUDITOR"],
            sequence=35,
        ),
    ],
)

_APPROVAL_POLICY = Policy(
    policy_id="ppm.approvals",
    name="Approval Workflow Access",
    description="Controls who can approve, reject, or escalate workflow items.",
    rules=[
        PolicyRule(
            rule_id="allow-pmo-admin-approve",
            description="PMO_ADMIN may approve or reject any workflow item.",
            effect=Effect.ALLOW,
            actions=["approvals:*"],
            resources=["*"],
            roles=["PMO_ADMIN"],
            sequence=10,
        ),
        PolicyRule(
            rule_id="allow-pm-approve",
            description="PM may approve items within their authority.",
            effect=Effect.ALLOW,
            actions=["approvals:approve", "approvals:reject", "approvals:read"],
            resources=["*"],
            roles=["PM"],
            sequence=20,
        ),
        PolicyRule(
            rule_id="allow-team-read",
            description="Team members may view approval status.",
            effect=Effect.ALLOW,
            actions=["approvals:read", "approvals:list"],
            resources=["*"],
            roles=["TEAM_MEMBER", "COLLABORATOR", "AUDITOR"],
            sequence=30,
        ),
    ],
)

_BUILT_IN_POLICIES: dict[str, Policy] = {
    _AGENT_CONFIG_POLICY.policy_id: _AGENT_CONFIG_POLICY,
    _PROJECT_ACCESS_POLICY.policy_id: _PROJECT_ACCESS_POLICY,
    _APPROVAL_POLICY.policy_id: _APPROVAL_POLICY,
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class PolicyEngine:
    """
    Evaluates one or more policies against a given context.

    Policies are evaluated in registration order.  A single DENY decision
    from any policy causes an overall DENY (deny-overrides strategy).
    """

    def __init__(self) -> None:
        self._policies: dict[str, Policy] = dict(_BUILT_IN_POLICIES)

    def register_policy(self, policy: Policy) -> None:
        """Register or replace a policy by its policy_id."""
        self._policies[policy.policy_id] = policy

    def get_policy(self, policy_id: str) -> Policy | None:
        return self._policies.get(policy_id)

    def list_policy_ids(self) -> list[str]:
        return list(self._policies)

    def evaluate(
        self,
        ctx: PolicyContext,
        policy_ids: list[str] | None = None,
    ) -> PolicyDecision:
        """
        Evaluate relevant policies and return an aggregate decision.

        Args:
            ctx: The context describing the subject, action, and resource.
            policy_ids: If given, only these policies are evaluated.
                        Defaults to all registered policies.

        Returns:
            ALLOW if all evaluated policies allow the action;
            DENY with the first DENY decision's details otherwise.
        """
        ids = policy_ids if policy_ids is not None else list(self._policies)
        last_allow: PolicyDecision | None = None

        for pid in ids:
            policy = self._policies.get(pid)
            if policy is None:
                logger.warning("Unknown policy_id requested: %s", pid)
                continue
            decision = policy.evaluate(ctx)
            if decision.effect == Effect.DENY:
                return decision
            last_allow = decision

        if last_allow is not None:
            return last_allow

        # No policies matched at all → default deny
        return PolicyDecision(
            effect=Effect.DENY,
            policy_id="__engine__",
            rule_id="__no_policy__",
            reason="No applicable policies found.",
        )

    def is_allowed(
        self,
        subject: str,
        action: str,
        resource: str,
        *,
        roles: list[str] | None = None,
        tenant_id: str | None = None,
        attributes: dict[str, Any] | None = None,
        policy_ids: list[str] | None = None,
    ) -> bool:
        """Convenience wrapper that returns a boolean ALLOW/DENY."""
        ctx = PolicyContext(
            subject=subject,
            action=action,
            resource=resource,
            roles=roles or [],
            tenant_id=tenant_id,
            attributes=attributes or {},
        )
        return self.evaluate(ctx, policy_ids=policy_ids).allowed


_default_engine: PolicyEngine | None = None


def get_default_engine() -> PolicyEngine:
    """Return the shared singleton :class:`PolicyEngine` instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = PolicyEngine()
    return _default_engine

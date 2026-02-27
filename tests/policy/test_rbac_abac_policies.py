from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RBAC_PATH = REPO_ROOT / "ops" / "config" / "rbac" / "roles.yaml"
ABAC_PATH = REPO_ROOT / "ops" / "config" / "abac" / "rules.yaml"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _rbac_allows(roles_cfg: dict, role: str, action: str, resource: str) -> bool:
    roles = {entry["id"]: entry.get("permissions", []) for entry in roles_cfg.get("roles", [])}
    perms = roles.get(role, [])
    allowed_pairs: set[tuple[str, str]] = set()
    for perm in perms:
        if isinstance(perm, dict):
            allowed_pairs.add((perm.get("action", ""), perm.get("resource", "")))
        elif isinstance(perm, str) and "." in perm:
            res, act = perm.rsplit(".", 1)
            allowed_pairs.add((act, res))
    return (action, resource) in allowed_pairs


def _abac_allows(abac_cfg: dict, role: str, action: str, resource: dict) -> bool:
    for rule in abac_cfg.get("rules", []):
        when = rule.get("when", {})
        action_in = when.get("action_in", [])
        resource_type = when.get("resource_type")
        regulated = when.get("resource_attributes", {}).get("regulatory_category")
        allowed_roles = set(when.get("subject_roles_allowed", []))

        if (
            action in action_in
            and resource.get("type") == resource_type
            and resource.get("regulatory_category") == regulated
            and role not in allowed_roles
            and rule.get("effect") == "deny"
        ):
            return False

    return abac_cfg.get("default_decision", "allow") == "allow"


def test_rbac_role_permissions_present() -> None:
    roles_cfg = _load_yaml(RBAC_PATH)

    assert _rbac_allows(roles_cfg, "portfolio_admin", "write", "portfolio")
    assert _rbac_allows(roles_cfg, "project_manager", "write", "project")
    assert _rbac_allows(roles_cfg, "portfolio_admin", "sync", "connector")
    assert _rbac_allows(roles_cfg, "auditor", "read", "audit")


def test_abac_denies_high_regulatory_project_for_non_compliance_role() -> None:
    abac_cfg = _load_yaml(ABAC_PATH)

    allowed = _abac_allows(
        abac_cfg,
        role="project_manager",
        action="read",
        resource={"type": "project", "regulatory_category": "high"},
    )

    assert not allowed


def test_abac_allows_high_regulatory_project_for_compliance_officer() -> None:
    abac_cfg = _load_yaml(ABAC_PATH)

    allowed = _abac_allows(
        abac_cfg,
        role="compliance_officer",
        action="read",
        resource={"type": "project", "regulatory_category": "high"},
    )

    assert allowed

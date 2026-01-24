from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set


CLASSIFICATION_ORDER = {
    "Public": 0,
    "Internal": 1,
    "Confidential": 2,
    "Restricted": 3,
}

DEFAULT_CLASSIFICATION = "Internal"


@dataclass(frozen=True)
class User:
    id: str
    name: str
    email: str | None
    role: str
    clearance: str


# Prototype RBAC matrix: (action -> allowed roles).
# This is intentionally permissive to keep the prototype usable; it still models the idea of role gates.
RBAC: Dict[str, Set[str]] = {
    "view": {"Any"},
    "create": {"Admin", "PMO", "PortfolioManager", "ProgramManager", "ProjectManager", "ResourceManager", "Finance", "Compliance", "VendorManager"},
    "edit": {"Admin", "PMO", "PortfolioManager", "ProgramManager", "ProjectManager", "ResourceManager", "Finance", "Compliance", "VendorManager"},
    "approve": {"Admin", "PMO", "Executive", "Finance"},
    "configure": {"Admin", "PMO"},
    "run_agent": {"Admin", "PMO", "PortfolioManager", "ProgramManager", "ProjectManager", "ResourceManager", "Finance", "Compliance", "VendorManager", "Executive"},
}


def can_access_classification(user_clearance: str, entity_classification: str) -> bool:
    u = CLASSIFICATION_ORDER.get(user_clearance, 0)
    e = CLASSIFICATION_ORDER.get(entity_classification, 0)
    return u >= e


def can_role(user_role: str, action: str) -> bool:
    allowed = RBAC.get(action, {"Admin"})
    return "Any" in allowed or user_role in allowed


def allowed_classifications_for_user(user_clearance: str) -> List[str]:
    max_level = CLASSIFICATION_ORDER.get(user_clearance, 0)
    # user can create at or below their clearance
    return [c for c, lvl in CLASSIFICATION_ORDER.items() if lvl <= max_level]

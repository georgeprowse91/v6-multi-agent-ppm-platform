"""Demand Intake Agent - Data models and event schemas.

The DemandCreatedEvent is imported from the shared ``events`` package.
Local demand record shapes are documented here for reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DemandRecord:
    """In-memory representation of an intake demand item."""

    demand_id: str
    title: str
    description: str
    business_objective: str
    category: str
    status: str
    created_at: str
    created_by: str
    business_unit: str = ""
    urgency: str = "Medium"
    source: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "demand_id": self.demand_id,
            "title": self.title,
            "description": self.description,
            "business_objective": self.business_objective,
            "category": self.category,
            "status": self.status,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "business_unit": self.business_unit,
            "urgency": self.urgency,
            "source": self.source,
        }

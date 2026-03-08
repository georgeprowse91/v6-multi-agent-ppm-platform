"""
Pydantic models and configuration constants for the Program Management Agent.

This module contains default configuration values, type definitions,
and any data models used by the program management domain.
"""

# Default dependency types supported by the program management agent
DEFAULT_DEPENDENCY_TYPES: list[str] = [
    "finish_to_start",
    "start_to_start",
    "finish_to_finish",
    "start_to_finish",
    "shared_resource",
    "technical_dependency",
    "deliverable_dependency",
]

# Default health score weights for composite health calculation
DEFAULT_HEALTH_SCORE_WEIGHTS: dict[str, float] = {
    "schedule": 0.25,
    "budget": 0.25,
    "risk": 0.20,
    "quality": 0.15,
    "resource": 0.15,
}

# Default optimization objective weights
DEFAULT_OPTIMIZATION_OBJECTIVES: dict[str, float] = {
    "utilization": 0.3,
    "cost": 0.2,
    "risk": 0.2,
    "schedule": 0.15,
    "alignment": 0.1,
    "synergy": 0.05,
}

# Valid actions for the program management agent
VALID_ACTIONS: list[str] = [
    "create_program",
    "generate_roadmap",
    "track_dependencies",
    "aggregate_benefits",
    "coordinate_resources",
    "identify_synergies",
    "analyze_change_impact",
    "get_program_health",
    "optimize_program",
    "submit_program_for_approval",
    "record_program_decision",
    "get_program",
    "list_dependency_graphs",
    "get_dependency_graph",
    "delete_dependency_graph",
]

# Required fields for program creation
PROGRAM_REQUIRED_FIELDS: list[str] = [
    "name",
    "description",
    "strategic_objectives",
    "constituent_projects",
]

# Actions that require a program_id
PROGRAM_ID_REQUIRED_ACTIONS: list[str] = [
    "track_dependencies",
    "analyze_change_impact",
    "get_dependency_graph",
    "delete_dependency_graph",
    "optimize_program",
    "submit_program_for_approval",
    "record_program_decision",
]

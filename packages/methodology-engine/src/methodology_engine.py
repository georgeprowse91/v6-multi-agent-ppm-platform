"""
Methodology Engine

Provides project methodology templates (Waterfall, Agile, PRINCE2, SAFe, Hybrid)
and phase/gate definitions used by delivery and governance agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Methodology(StrEnum):
    """Supported project methodology types."""

    WATERFALL = "waterfall"
    AGILE = "agile"
    PRINCE2 = "prince2"
    SAFE = "safe"
    HYBRID = "hybrid"
    LEAN = "lean"
    KANBAN = "kanban"


@dataclass
class MethodologyPhase:
    """A single phase or sprint-type unit within a methodology."""

    phase_id: str
    name: str
    description: str
    sequence: int
    gate_required: bool = False
    deliverables: list[str] = field(default_factory=list)
    approvals_required: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "name": self.name,
            "description": self.description,
            "sequence": self.sequence,
            "gate_required": self.gate_required,
            "deliverables": self.deliverables,
            "approvals_required": self.approvals_required,
        }


@dataclass
class MethodologyTemplate:
    """A complete methodology definition including all phases."""

    methodology: Methodology
    display_name: str
    description: str
    phases: list[MethodologyPhase] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "methodology": self.methodology.value,
            "display_name": self.display_name,
            "description": self.description,
            "phases": [p.to_dict() for p in self.phases],
            "metadata": self.metadata,
        }

    def get_phase(self, phase_id: str) -> MethodologyPhase | None:
        for phase in self.phases:
            if phase.phase_id == phase_id:
                return phase
        return None

    def get_gate_phases(self) -> list[MethodologyPhase]:
        return [p for p in self.phases if p.gate_required]


# ---------------------------------------------------------------------------
# Built-in methodology templates
# ---------------------------------------------------------------------------

_WATERFALL_TEMPLATE = MethodologyTemplate(
    methodology=Methodology.WATERFALL,
    display_name="Waterfall",
    description="Sequential, plan-driven project delivery with formal phase gates.",
    phases=[
        MethodologyPhase(
            phase_id="initiation",
            name="Initiation",
            description="Define project objectives, scope, and feasibility.",
            sequence=1,
            gate_required=True,
            deliverables=["Project Charter", "Feasibility Study"],
            approvals_required=["sponsor"],
        ),
        MethodologyPhase(
            phase_id="planning",
            name="Planning",
            description="Develop detailed project plan, schedule, and resource allocation.",
            sequence=2,
            gate_required=True,
            deliverables=["Project Management Plan", "WBS", "Risk Register"],
            approvals_required=["pmo", "sponsor"],
        ),
        MethodologyPhase(
            phase_id="execution",
            name="Execution",
            description="Implement planned activities and produce deliverables.",
            sequence=3,
            gate_required=False,
            deliverables=["Deliverables", "Status Reports"],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="monitoring",
            name="Monitoring & Control",
            description="Track progress, manage changes, and control scope.",
            sequence=4,
            gate_required=False,
            deliverables=["Progress Reports", "Change Requests"],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="closure",
            name="Closure",
            description="Formalise project completion, capture lessons learned.",
            sequence=5,
            gate_required=True,
            deliverables=["Closure Report", "Lessons Learned", "Benefits Realisation Plan"],
            approvals_required=["sponsor", "pmo"],
        ),
    ],
    metadata={"standard": "PMBoK", "iteration_based": False},
)

_AGILE_TEMPLATE = MethodologyTemplate(
    methodology=Methodology.AGILE,
    display_name="Agile (Scrum)",
    description="Iterative, incremental delivery using time-boxed sprints.",
    phases=[
        MethodologyPhase(
            phase_id="product_vision",
            name="Product Vision",
            description="Define product vision, backlog, and release roadmap.",
            sequence=1,
            gate_required=True,
            deliverables=["Product Vision Statement", "Initial Product Backlog"],
            approvals_required=["product_owner"],
        ),
        MethodologyPhase(
            phase_id="sprint_planning",
            name="Sprint Planning",
            description="Select backlog items for the sprint and create sprint goal.",
            sequence=2,
            gate_required=False,
            deliverables=["Sprint Backlog", "Sprint Goal"],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="sprint_execution",
            name="Sprint Execution",
            description="Daily scrum, development, and testing within the sprint.",
            sequence=3,
            gate_required=False,
            deliverables=["Potentially Shippable Increment"],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="sprint_review",
            name="Sprint Review & Retrospective",
            description="Demonstrate increment to stakeholders and improve the process.",
            sequence=4,
            gate_required=False,
            deliverables=["Sprint Review Notes", "Retrospective Actions"],
            approvals_required=["product_owner"],
        ),
        MethodologyPhase(
            phase_id="release",
            name="Release",
            description="Deploy production-ready increment and update stakeholders.",
            sequence=5,
            gate_required=True,
            deliverables=["Release Notes", "Deployed Increment"],
            approvals_required=["product_owner", "release_manager"],
        ),
    ],
    metadata={"standard": "Scrum Guide", "iteration_based": True, "iteration_length_weeks": 2},
)

_PRINCE2_TEMPLATE = MethodologyTemplate(
    methodology=Methodology.PRINCE2,
    display_name="PRINCE2",
    description="Process-based framework with defined roles, themes, and stage gates.",
    phases=[
        MethodologyPhase(
            phase_id="su",
            name="Starting Up a Project (SU)",
            description="Appoint project team, create project brief.",
            sequence=1,
            gate_required=True,
            deliverables=["Project Brief", "Outline Business Case"],
            approvals_required=["project_board"],
        ),
        MethodologyPhase(
            phase_id="ip",
            name="Initiating a Project (IP)",
            description="Elaborate planning, create Project Initiation Documentation.",
            sequence=2,
            gate_required=True,
            deliverables=["PID", "Business Case", "Risk Register", "Quality Plan"],
            approvals_required=["project_board"],
        ),
        MethodologyPhase(
            phase_id="cs",
            name="Controlling a Stage (CS)",
            description="Monitor progress, manage issues, and report to project board.",
            sequence=3,
            gate_required=False,
            deliverables=["Checkpoint Reports", "Issue Reports"],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="mp",
            name="Managing Product Delivery (MP)",
            description="Team managers accept, execute, and deliver work packages.",
            sequence=4,
            gate_required=False,
            deliverables=["Work Packages", "Quality Records"],
            approvals_required=["project_manager"],
        ),
        MethodologyPhase(
            phase_id="sb",
            name="Managing a Stage Boundary (SB)",
            description="Plan next stage, update business case, seek board approval.",
            sequence=5,
            gate_required=True,
            deliverables=["Next Stage Plan", "Updated Business Case"],
            approvals_required=["project_board"],
        ),
        MethodologyPhase(
            phase_id="cp",
            name="Closing a Project (CP)",
            description="Hand over products, evaluate benefits, recommend closure.",
            sequence=6,
            gate_required=True,
            deliverables=["End Project Report", "Benefits Review Plan", "Lessons Report"],
            approvals_required=["project_board"],
        ),
    ],
    metadata={"standard": "PRINCE2 2017", "iteration_based": False},
)

_SAFE_TEMPLATE = MethodologyTemplate(
    methodology=Methodology.SAFE,
    display_name="SAFe (Scaled Agile)",
    description="Scaled Agile Framework for enterprise-scale delivery using ARTs and PIs.",
    phases=[
        MethodologyPhase(
            phase_id="portfolio_vision",
            name="Portfolio Vision & Roadmap",
            description="Define strategic themes and portfolio Kanban.",
            sequence=1,
            gate_required=True,
            deliverables=["Strategic Themes", "Portfolio Kanban", "Lean Budget"],
            approvals_required=["epic_owner", "rtae"],
        ),
        MethodologyPhase(
            phase_id="pi_planning",
            name="PI Planning",
            description="Two-day event to align teams to a shared mission and roadmap.",
            sequence=2,
            gate_required=True,
            deliverables=["PI Objectives", "Team Iteration Plans", "Risk Board"],
            approvals_required=["release_train_engineer"],
        ),
        MethodologyPhase(
            phase_id="iteration_execution",
            name="Iteration Execution",
            description="Teams execute iterations and integrate continuously.",
            sequence=3,
            gate_required=False,
            deliverables=["Integrated Increment", "Metrics"],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="system_demo",
            name="System Demo",
            description="Demonstrate integrated solution to stakeholders every iteration.",
            sequence=4,
            gate_required=False,
            deliverables=["Demo Artefacts", "Accepted Features"],
            approvals_required=["product_management"],
        ),
        MethodologyPhase(
            phase_id="inspect_adapt",
            name="Inspect & Adapt",
            description="PI-level retrospective and problem-solving workshop.",
            sequence=5,
            gate_required=True,
            deliverables=["PI System Demo", "I&A Workshop Report", "Improvement Backlog"],
            approvals_required=["release_train_engineer", "business_owner"],
        ),
    ],
    metadata={"standard": "SAFe 6.0", "iteration_based": True, "pi_length_weeks": 12},
)

_HYBRID_TEMPLATE = MethodologyTemplate(
    methodology=Methodology.HYBRID,
    display_name="Hybrid",
    description="Combines sequential governance gates with agile delivery sprints.",
    phases=[
        MethodologyPhase(
            phase_id="define",
            name="Define",
            description="Establish project scope, objectives, and governance approach.",
            sequence=1,
            gate_required=True,
            deliverables=["Project Charter", "Delivery Approach"],
            approvals_required=["sponsor"],
        ),
        MethodologyPhase(
            phase_id="design",
            name="Design",
            description="Architecture, UX and solution design with stakeholder validation.",
            sequence=2,
            gate_required=True,
            deliverables=["Solution Design", "Architecture Decision Records"],
            approvals_required=["architect", "pmo"],
        ),
        MethodologyPhase(
            phase_id="build",
            name="Build (Agile Sprints)",
            description="Iterative development with regular sprint reviews.",
            sequence=3,
            gate_required=False,
            deliverables=["Sprint Increments", "Test Reports"],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="test",
            name="Test & Validate",
            description="User acceptance testing and performance validation.",
            sequence=4,
            gate_required=True,
            deliverables=["UAT Sign-off", "Performance Test Results"],
            approvals_required=["business_owner"],
        ),
        MethodologyPhase(
            phase_id="deploy",
            name="Deploy & Transition",
            description="Production deployment, training, and handover to operations.",
            sequence=5,
            gate_required=True,
            deliverables=["Deployment Package", "Training Material", "Operations Runbook"],
            approvals_required=["release_manager", "sponsor"],
        ),
    ],
    metadata={"standard": "custom", "iteration_based": True},
)

_LEAN_TEMPLATE = MethodologyTemplate(
    methodology=Methodology.LEAN,
    display_name="Lean",
    description="Continuous-flow delivery focused on eliminating waste and maximising value.",
    phases=[
        MethodologyPhase(
            phase_id="value_stream_mapping",
            name="Value Stream Mapping",
            description="Identify and map the current-state value stream to surface waste.",
            sequence=1,
            gate_required=False,
            deliverables=["Current-state VSM", "Waste Register"],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="kaizen",
            name="Kaizen (Continuous Improvement)",
            description="Targeted improvement events to eliminate identified waste.",
            sequence=2,
            gate_required=False,
            deliverables=["Future-state VSM", "Kaizen Report"],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="implement",
            name="Implement & Sustain",
            description="Embed improvements and establish standard work.",
            sequence=3,
            gate_required=False,
            deliverables=["Standard Work Documents", "Control Plan"],
            approvals_required=["process_owner"],
        ),
    ],
    metadata={"standard": "Lean / Toyota Production System", "iteration_based": True},
)

_KANBAN_TEMPLATE = MethodologyTemplate(
    methodology=Methodology.KANBAN,
    display_name="Kanban",
    description="Flow-based delivery visualised on a Kanban board with WIP limits.",
    phases=[
        MethodologyPhase(
            phase_id="backlog",
            name="Backlog",
            description="Unprioritised requests awaiting intake.",
            sequence=1,
            gate_required=False,
            deliverables=[],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="ready",
            name="Ready",
            description="Prioritised items ready for the team to pull.",
            sequence=2,
            gate_required=False,
            deliverables=[],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="in_progress",
            name="In Progress",
            description="Work actively being done (WIP-limited).",
            sequence=3,
            gate_required=False,
            deliverables=[],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="review",
            name="Review",
            description="Completed work awaiting verification.",
            sequence=4,
            gate_required=False,
            deliverables=[],
            approvals_required=[],
        ),
        MethodologyPhase(
            phase_id="done",
            name="Done",
            description="Verified and deployed work items.",
            sequence=5,
            gate_required=False,
            deliverables=[],
            approvals_required=[],
        ),
    ],
    metadata={"standard": "Kanban Method", "iteration_based": False},
)

_BUILT_IN_TEMPLATES: dict[Methodology, MethodologyTemplate] = {
    Methodology.WATERFALL: _WATERFALL_TEMPLATE,
    Methodology.AGILE: _AGILE_TEMPLATE,
    Methodology.PRINCE2: _PRINCE2_TEMPLATE,
    Methodology.SAFE: _SAFE_TEMPLATE,
    Methodology.HYBRID: _HYBRID_TEMPLATE,
    Methodology.LEAN: _LEAN_TEMPLATE,
    Methodology.KANBAN: _KANBAN_TEMPLATE,
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class MethodologyEngine:
    """
    Central registry for methodology templates.

    Supports built-in templates and allows registration of custom templates
    at runtime.
    """

    def __init__(self) -> None:
        self._templates: dict[Methodology, MethodologyTemplate] = dict(_BUILT_IN_TEMPLATES)

    def get_template(self, methodology: Methodology | str) -> MethodologyTemplate:
        """Return the template for the given methodology.

        Args:
            methodology: A :class:`Methodology` value or its string key.

        Raises:
            ValueError: If the methodology is not registered.
        """
        key = Methodology(methodology) if isinstance(methodology, str) else methodology
        try:
            return self._templates[key]
        except KeyError:
            raise ValueError(f"Unknown methodology: {methodology}") from None

    def register_template(self, template: MethodologyTemplate) -> None:
        """Register or replace a methodology template."""
        self._templates[template.methodology] = template

    def list_methodologies(self) -> list[str]:
        """Return the names of all registered methodologies."""
        return [m.value for m in self._templates]

    def get_phases(self, methodology: Methodology | str) -> list[MethodologyPhase]:
        """Convenience helper – return phases for a methodology."""
        return self.get_template(methodology).phases

    def get_gate_phases(self, methodology: Methodology | str) -> list[MethodologyPhase]:
        """Return only the phases that require a formal gate review."""
        return self.get_template(methodology).get_gate_phases()

    def recommend_methodology(self, context: dict[str, Any]) -> Methodology:
        """
        Recommend a methodology based on project context signals.

        Context keys (all optional):
            team_size (int): Number of team members.
            requirements_stability (str): 'stable' | 'evolving' | 'unknown'.
            delivery_cadence (str): 'fixed' | 'iterative' | 'continuous'.
            organisation_scale (str): 'small' | 'medium' | 'enterprise'.
            regulatory_compliance (bool): True if strict compliance is needed.
        """
        scale = context.get("organisation_scale", "small")
        cadence = context.get("delivery_cadence", "iterative")
        stability = context.get("requirements_stability", "evolving")
        regulatory = context.get("regulatory_compliance", False)
        team_size = int(context.get("team_size", 5))

        if regulatory and stability == "stable":
            return Methodology.PRINCE2

        if scale == "enterprise" and cadence == "iterative":
            return Methodology.SAFE

        if cadence == "continuous" and team_size < 20:
            return Methodology.KANBAN

        if stability == "stable" and cadence == "fixed":
            return Methodology.WATERFALL

        if cadence == "iterative" and team_size <= 50:
            return Methodology.AGILE

        return Methodology.HYBRID


_default_engine: MethodologyEngine | None = None


def get_default_engine() -> MethodologyEngine:
    """Return the shared singleton :class:`MethodologyEngine` instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = MethodologyEngine()
    return _default_engine

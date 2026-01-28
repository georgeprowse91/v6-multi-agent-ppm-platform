from __future__ import annotations

from typing import Any


METHODOLOGY_MAPS: dict[str, dict[str, Any]] = {
    "agile": {
        "id": "agile",
        "name": "Agile Delivery",
        "description": "Iterative delivery with rapid feedback cycles.",
        "stages": [
            {
                "id": "agile-discovery",
                "name": "Discovery",
                "activities": [
                    {
                        "id": "agile-vision",
                        "name": "Vision alignment",
                        "description": "Define the product vision and success criteria.",
                        "prerequisites": [],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "agile-stakeholder-map",
                        "name": "Stakeholder map",
                        "description": "Identify sponsors, users, and delivery partners.",
                        "prerequisites": ["agile-vision"],
                        "category": "methodology",
                        "recommended_canvas_tab": "tree",
                    },
                ],
            },
            {
                "id": "agile-planning",
                "name": "Planning",
                "activities": [
                    {
                        "id": "agile-backlog",
                        "name": "Backlog definition",
                        "description": "Capture epics and prioritize the delivery backlog.",
                        "prerequisites": ["agile-vision"],
                        "category": "methodology",
                        "recommended_canvas_tab": "spreadsheet",
                    },
                    {
                        "id": "agile-release-plan",
                        "name": "Release planning",
                        "description": "Sequence releases and define sprint goals.",
                        "prerequisites": ["agile-backlog"],
                        "category": "methodology",
                        "recommended_canvas_tab": "timeline",
                    },
                ],
            },
            {
                "id": "agile-delivery",
                "name": "Delivery",
                "activities": [
                    {
                        "id": "agile-sprint-planning",
                        "name": "Sprint planning",
                        "description": "Commit to sprint scope and capacity.",
                        "prerequisites": ["agile-release-plan"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "agile-standups",
                        "name": "Daily standups",
                        "description": "Coordinate daily delivery progress and blockers.",
                        "prerequisites": ["agile-sprint-planning"],
                        "category": "methodology",
                        "recommended_canvas_tab": "dashboard",
                    },
                ],
            },
            {
                "id": "agile-review",
                "name": "Review",
                "activities": [
                    {
                        "id": "agile-sprint-review",
                        "name": "Sprint review",
                        "description": "Validate delivered work with stakeholders.",
                        "prerequisites": ["agile-standups"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "agile-retrospective",
                        "name": "Retrospective",
                        "description": "Capture lessons learned and improvement actions.",
                        "prerequisites": ["agile-sprint-review"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                ],
            },
        ],
        "monitoring": [
            {
                "id": "monitoring-health",
                "name": "Team health check",
                "description": "Track delivery morale, workload, and capacity.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-risks",
                "name": "Risk review",
                "description": "Review open risks and mitigation actions.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "document",
            },
            {
                "id": "monitoring-dependencies",
                "name": "Dependency tracking",
                "description": "Maintain cross-team dependencies and handoffs.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "spreadsheet",
            },
            {
                "id": "monitoring-metrics",
                "name": "Delivery metrics",
                "description": "Review throughput, lead time, and quality metrics.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-change",
                "name": "Change log",
                "description": "Capture scope change decisions and approvals.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "timeline",
            },
        ],
    },
    "waterfall": {
        "id": "waterfall",
        "name": "Waterfall",
        "description": "Sequential planning and delivery with phase gates.",
        "stages": [
            {
                "id": "waterfall-requirements",
                "name": "Requirements",
                "activities": [
                    {
                        "id": "waterfall-scope",
                        "name": "Scope definition",
                        "description": "Define project scope, objectives, and constraints.",
                        "prerequisites": [],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "waterfall-requirements",
                        "name": "Requirements baseline",
                        "description": "Document functional and non-functional requirements.",
                        "prerequisites": ["waterfall-scope"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                ],
            },
            {
                "id": "waterfall-design",
                "name": "Design",
                "activities": [
                    {
                        "id": "waterfall-architecture",
                        "name": "Solution architecture",
                        "description": "Define architecture, interfaces, and standards.",
                        "prerequisites": ["waterfall-requirements"],
                        "category": "methodology",
                        "recommended_canvas_tab": "tree",
                    },
                    {
                        "id": "waterfall-workplan",
                        "name": "Work plan",
                        "description": "Build the delivery plan and schedule.",
                        "prerequisites": ["waterfall-architecture"],
                        "category": "methodology",
                        "recommended_canvas_tab": "timeline",
                    },
                ],
            },
            {
                "id": "waterfall-build",
                "name": "Build",
                "activities": [
                    {
                        "id": "waterfall-implementation",
                        "name": "Implementation",
                        "description": "Deliver scoped functionality according to design.",
                        "prerequisites": ["waterfall-workplan"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "waterfall-integration",
                        "name": "Integration",
                        "description": "Integrate components and verify end-to-end flows.",
                        "prerequisites": ["waterfall-implementation"],
                        "category": "methodology",
                        "recommended_canvas_tab": "tree",
                    },
                ],
            },
            {
                "id": "waterfall-validation",
                "name": "Validation",
                "activities": [
                    {
                        "id": "waterfall-testing",
                        "name": "System testing",
                        "description": "Execute validation and test protocols.",
                        "prerequisites": ["waterfall-integration"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "waterfall-acceptance",
                        "name": "Business acceptance",
                        "description": "Obtain sign-off for release readiness.",
                        "prerequisites": ["waterfall-testing"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                ],
            },
        ],
        "monitoring": [
            {
                "id": "monitoring-health",
                "name": "Team health check",
                "description": "Track delivery morale, workload, and capacity.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-risks",
                "name": "Risk review",
                "description": "Review open risks and mitigation actions.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "document",
            },
            {
                "id": "monitoring-dependencies",
                "name": "Dependency tracking",
                "description": "Maintain cross-team dependencies and handoffs.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "spreadsheet",
            },
            {
                "id": "monitoring-metrics",
                "name": "Delivery metrics",
                "description": "Review throughput, lead time, and quality metrics.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-change",
                "name": "Change log",
                "description": "Capture scope change decisions and approvals.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "timeline",
            },
        ],
    },
    "hybrid": {
        "id": "hybrid",
        "name": "Hybrid",
        "description": "Blend of staged planning with iterative delivery.",
        "stages": [
            {
                "id": "hybrid-discovery",
                "name": "Discovery",
                "activities": [
                    {
                        "id": "hybrid-intake",
                        "name": "Intake alignment",
                        "description": "Confirm objectives, constraints, and outcomes.",
                        "prerequisites": [],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "hybrid-feasibility",
                        "name": "Feasibility review",
                        "description": "Validate scope, feasibility, and resourcing.",
                        "prerequisites": ["hybrid-intake"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                ],
            },
            {
                "id": "hybrid-planning",
                "name": "Planning",
                "activities": [
                    {
                        "id": "hybrid-roadmap",
                        "name": "Roadmap planning",
                        "description": "Define milestones and release sequence.",
                        "prerequisites": ["hybrid-feasibility"],
                        "category": "methodology",
                        "recommended_canvas_tab": "timeline",
                    },
                    {
                        "id": "hybrid-backlog",
                        "name": "Backlog refinement",
                        "description": "Prioritize backlog and acceptance criteria.",
                        "prerequisites": ["hybrid-roadmap"],
                        "category": "methodology",
                        "recommended_canvas_tab": "spreadsheet",
                    },
                ],
            },
            {
                "id": "hybrid-delivery",
                "name": "Delivery",
                "activities": [
                    {
                        "id": "hybrid-iterations",
                        "name": "Iteration delivery",
                        "description": "Execute incremental delivery cycles.",
                        "prerequisites": ["hybrid-backlog"],
                        "category": "methodology",
                        "recommended_canvas_tab": "dashboard",
                    },
                    {
                        "id": "hybrid-integration",
                        "name": "Integration readiness",
                        "description": "Validate integration readiness across teams.",
                        "prerequisites": ["hybrid-iterations"],
                        "category": "methodology",
                        "recommended_canvas_tab": "tree",
                    },
                ],
            },
            {
                "id": "hybrid-transition",
                "name": "Transition",
                "activities": [
                    {
                        "id": "hybrid-release",
                        "name": "Release coordination",
                        "description": "Coordinate go-live and stakeholder readiness.",
                        "prerequisites": ["hybrid-integration"],
                        "category": "methodology",
                        "recommended_canvas_tab": "timeline",
                    },
                    {
                        "id": "hybrid-lessons",
                        "name": "Lessons capture",
                        "description": "Capture lessons learned and next steps.",
                        "prerequisites": ["hybrid-release"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                ],
            },
        ],
        "monitoring": [
            {
                "id": "monitoring-health",
                "name": "Team health check",
                "description": "Track delivery morale, workload, and capacity.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-risks",
                "name": "Risk review",
                "description": "Review open risks and mitigation actions.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "document",
            },
            {
                "id": "monitoring-dependencies",
                "name": "Dependency tracking",
                "description": "Maintain cross-team dependencies and handoffs.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "spreadsheet",
            },
            {
                "id": "monitoring-metrics",
                "name": "Delivery metrics",
                "description": "Review throughput, lead time, and quality metrics.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-change",
                "name": "Change log",
                "description": "Capture scope change decisions and approvals.",
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "timeline",
            },
        ],
    },
}


def available_methodologies() -> list[str]:
    return list(METHODOLOGY_MAPS.keys())


def get_methodology_map(methodology_id: str | None) -> dict[str, Any]:
    if methodology_id and methodology_id in METHODOLOGY_MAPS:
        return METHODOLOGY_MAPS[methodology_id]
    return METHODOLOGY_MAPS["agile"]

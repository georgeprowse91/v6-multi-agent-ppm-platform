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
                        "assistant_prompts": [
                            "Draft the product vision statement and success criteria.",
                            "Validate the vision against business goals and constraints.",
                            "Recommend next steps to engage key stakeholders.",
                        ],
                        "prerequisites": [],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "agile-stakeholder-map",
                        "name": "Stakeholder map",
                        "description": "Identify sponsors, users, and delivery partners.",
                        "assistant_prompts": [
                            "Create a stakeholder map with roles, influence, and engagement needs.",
                            "Check that all sponsors, users, and delivery partners are captured.",
                            "Recommend next steps to define the delivery backlog.",
                        ],
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
                        "assistant_prompts": [
                            "Draft an initial backlog of epics with priorities and outcomes.",
                            "Verify backlog items align to the product vision and user needs.",
                            "Recommend next steps for release planning.",
                        ],
                        "prerequisites": ["agile-vision"],
                        "category": "methodology",
                        "recommended_canvas_tab": "spreadsheet",
                    },
                    {
                        "id": "agile-release-plan",
                        "name": "Release planning",
                        "description": "Sequence releases and define sprint goals.",
                        "assistant_prompts": [
                            "Create a high-level release plan with sprint goals and sequencing.",
                            "Validate capacity assumptions and dependency timing for releases.",
                            "Recommend next steps for sprint planning.",
                        ],
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
                        "assistant_prompts": [
                            "Draft sprint scope, goals, and capacity commitments.",
                            "Check that the sprint backlog is feasible with available capacity.",
                            "Recommend next steps for daily standups.",
                        ],
                        "prerequisites": ["agile-release-plan"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "agile-standups",
                        "name": "Daily standups",
                        "description": "Coordinate daily delivery progress and blockers.",
                        "assistant_prompts": [
                            "Create a daily standup agenda and tracking checklist.",
                            "Validate blockers and dependencies are being captured and tracked.",
                            "Recommend next steps leading into the sprint review.",
                        ],
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
                        "assistant_prompts": [
                            "Draft a sprint review outline and demo checklist.",
                            "Validate delivered work against acceptance criteria.",
                            "Recommend next steps for the retrospective.",
                        ],
                        "prerequisites": ["agile-standups"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "agile-retrospective",
                        "name": "Retrospective",
                        "description": "Capture lessons learned and improvement actions.",
                        "assistant_prompts": [
                            "Create a retrospective summary with improvement actions.",
                            "Check that improvement actions have owners and due dates.",
                            "Recommend next steps to feed improvements into the backlog.",
                        ],
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
                "assistant_prompts": [
                    "Summarize team health signals and capacity notes.",
                    "Check for workload or morale risks that need escalation.",
                    "Recommend next steps to rebalance team capacity.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-risks",
                "name": "Risk review",
                "description": "Review open risks and mitigation actions.",
                "assistant_prompts": [
                    "Update the risk register with current status and mitigation actions.",
                    "Validate mitigation owners, dates, and residual risk levels.",
                    "Recommend next steps to address the top risks.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "document",
            },
            {
                "id": "monitoring-dependencies",
                "name": "Dependency tracking",
                "description": "Maintain cross-team dependencies and handoffs.",
                "assistant_prompts": [
                    "Create or update the dependency log with owners and due dates.",
                    "Check for upcoming dependency conflicts or blockers.",
                    "Recommend next steps to resolve critical dependencies.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "spreadsheet",
            },
            {
                "id": "monitoring-metrics",
                "name": "Delivery metrics",
                "description": "Review throughput, lead time, and quality metrics.",
                "assistant_prompts": [
                    "Compile delivery metrics for throughput, lead time, and quality.",
                    "Validate data quality and trend shifts versus baselines.",
                    "Recommend next steps based on the metric trends.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-change",
                "name": "Change log",
                "description": "Capture scope change decisions and approvals.",
                "assistant_prompts": [
                    "Update the change log with recent scope decisions and approvals.",
                    "Verify approvals, impacts, and dates are documented.",
                    "Recommend next steps to communicate recent changes.",
                ],
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
                        "assistant_prompts": [
                            "Draft the project scope statement with objectives and constraints.",
                            "Validate scope boundaries with sponsors and key assumptions.",
                            "Recommend next steps to baseline requirements.",
                        ],
                        "prerequisites": [],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "waterfall-requirements",
                        "name": "Requirements baseline",
                        "description": "Document functional and non-functional requirements.",
                        "assistant_prompts": [
                            "Create a requirements baseline covering functional and non-functional needs.",
                            "Check requirements for completeness and traceability to scope.",
                            "Recommend next steps for solution architecture.",
                        ],
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
                        "assistant_prompts": [
                            "Draft a solution architecture overview with interfaces and standards.",
                            "Validate architecture decisions against requirements and constraints.",
                            "Recommend next steps to build the work plan.",
                        ],
                        "prerequisites": ["waterfall-requirements"],
                        "category": "methodology",
                        "recommended_canvas_tab": "tree",
                    },
                    {
                        "id": "waterfall-workplan",
                        "name": "Work plan",
                        "description": "Build the delivery plan and schedule.",
                        "assistant_prompts": [
                            "Create the project work plan with milestones and schedule.",
                            "Check resource loading and critical path assumptions.",
                            "Recommend next steps for implementation.",
                        ],
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
                        "assistant_prompts": [
                            "Draft the implementation plan and deliverable checklist.",
                            "Validate readiness of environments and required resources.",
                            "Recommend next steps for integration.",
                        ],
                        "prerequisites": ["waterfall-workplan"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "waterfall-integration",
                        "name": "Integration",
                        "description": "Integrate components and verify end-to-end flows.",
                        "assistant_prompts": [
                            "Create an integration plan with sequencing and dependencies.",
                            "Check integration risks and test coverage for gaps.",
                            "Recommend next steps for system testing.",
                        ],
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
                        "assistant_prompts": [
                            "Draft the system test plan and execution checklist.",
                            "Validate test cases map to requirements and risk areas.",
                            "Recommend next steps for business acceptance.",
                        ],
                        "prerequisites": ["waterfall-integration"],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "waterfall-acceptance",
                        "name": "Business acceptance",
                        "description": "Obtain sign-off for release readiness.",
                        "assistant_prompts": [
                            "Prepare the acceptance package and sign-off checklist.",
                            "Check acceptance criteria and evidence are complete.",
                            "Recommend next steps for release readiness.",
                        ],
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
                "assistant_prompts": [
                    "Summarize team health signals and capacity notes.",
                    "Check for workload or morale risks that need escalation.",
                    "Recommend next steps to rebalance team capacity.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-risks",
                "name": "Risk review",
                "description": "Review open risks and mitigation actions.",
                "assistant_prompts": [
                    "Update the risk register with current status and mitigation actions.",
                    "Validate mitigation owners, dates, and residual risk levels.",
                    "Recommend next steps to address the top risks.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "document",
            },
            {
                "id": "monitoring-dependencies",
                "name": "Dependency tracking",
                "description": "Maintain cross-team dependencies and handoffs.",
                "assistant_prompts": [
                    "Create or update the dependency log with owners and due dates.",
                    "Check for upcoming dependency conflicts or blockers.",
                    "Recommend next steps to resolve critical dependencies.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "spreadsheet",
            },
            {
                "id": "monitoring-metrics",
                "name": "Delivery metrics",
                "description": "Review throughput, lead time, and quality metrics.",
                "assistant_prompts": [
                    "Compile delivery metrics for throughput, lead time, and quality.",
                    "Validate data quality and trend shifts versus baselines.",
                    "Recommend next steps based on the metric trends.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-change",
                "name": "Change log",
                "description": "Capture scope change decisions and approvals.",
                "assistant_prompts": [
                    "Update the change log with recent scope decisions and approvals.",
                    "Verify approvals, impacts, and dates are documented.",
                    "Recommend next steps to communicate recent changes.",
                ],
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
                        "assistant_prompts": [
                            "Draft the intake summary with objectives, constraints, and outcomes.",
                            "Validate alignment with sponsor expectations and priorities.",
                            "Recommend next steps for the feasibility review.",
                        ],
                        "prerequisites": [],
                        "category": "methodology",
                        "recommended_canvas_tab": "document",
                    },
                    {
                        "id": "hybrid-feasibility",
                        "name": "Feasibility review",
                        "description": "Validate scope, feasibility, and resourcing.",
                        "assistant_prompts": [
                            "Create a feasibility assessment covering scope, cost, and resourcing.",
                            "Check assumptions, risks, and constraints for gaps.",
                            "Recommend next steps for roadmap planning.",
                        ],
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
                        "assistant_prompts": [
                            "Draft roadmap milestones and release sequencing.",
                            "Validate dependencies and capacity assumptions for the roadmap.",
                            "Recommend next steps for backlog refinement.",
                        ],
                        "prerequisites": ["hybrid-feasibility"],
                        "category": "methodology",
                        "recommended_canvas_tab": "timeline",
                    },
                    {
                        "id": "hybrid-backlog",
                        "name": "Backlog refinement",
                        "description": "Prioritize backlog and acceptance criteria.",
                        "assistant_prompts": [
                            "Create a prioritized backlog with acceptance criteria.",
                            "Check backlog items for clarity, sizing, and readiness.",
                            "Recommend next steps for iteration delivery.",
                        ],
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
                        "assistant_prompts": [
                            "Draft an iteration plan with goals, scope, and cadence.",
                            "Validate progress tracking and blocker handling routines.",
                            "Recommend next steps for integration readiness.",
                        ],
                        "prerequisites": ["hybrid-backlog"],
                        "category": "methodology",
                        "recommended_canvas_tab": "dashboard",
                    },
                    {
                        "id": "hybrid-integration",
                        "name": "Integration readiness",
                        "description": "Validate integration readiness across teams.",
                        "assistant_prompts": [
                            "Create an integration readiness checklist across teams.",
                            "Check environment, data, and dependency readiness.",
                            "Recommend next steps for release coordination.",
                        ],
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
                        "assistant_prompts": [
                            "Draft a release coordination plan and cutover checklist.",
                            "Validate stakeholder readiness and communications coverage.",
                            "Recommend next steps for lessons capture.",
                        ],
                        "prerequisites": ["hybrid-integration"],
                        "category": "methodology",
                        "recommended_canvas_tab": "timeline",
                    },
                    {
                        "id": "hybrid-lessons",
                        "name": "Lessons capture",
                        "description": "Capture lessons learned and next steps.",
                        "assistant_prompts": [
                            "Capture a lessons learned summary with improvement actions.",
                            "Check that actions have owners and follow-up dates.",
                            "Recommend next steps to feed insights into planning.",
                        ],
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
                "assistant_prompts": [
                    "Summarize team health signals and capacity notes.",
                    "Check for workload or morale risks that need escalation.",
                    "Recommend next steps to rebalance team capacity.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-risks",
                "name": "Risk review",
                "description": "Review open risks and mitigation actions.",
                "assistant_prompts": [
                    "Update the risk register with current status and mitigation actions.",
                    "Validate mitigation owners, dates, and residual risk levels.",
                    "Recommend next steps to address the top risks.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "document",
            },
            {
                "id": "monitoring-dependencies",
                "name": "Dependency tracking",
                "description": "Maintain cross-team dependencies and handoffs.",
                "assistant_prompts": [
                    "Create or update the dependency log with owners and due dates.",
                    "Check for upcoming dependency conflicts or blockers.",
                    "Recommend next steps to resolve critical dependencies.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "spreadsheet",
            },
            {
                "id": "monitoring-metrics",
                "name": "Delivery metrics",
                "description": "Review throughput, lead time, and quality metrics.",
                "assistant_prompts": [
                    "Compile delivery metrics for throughput, lead time, and quality.",
                    "Validate data quality and trend shifts versus baselines.",
                    "Recommend next steps based on the metric trends.",
                ],
                "prerequisites": [],
                "category": "monitoring",
                "recommended_canvas_tab": "dashboard",
            },
            {
                "id": "monitoring-change",
                "name": "Change log",
                "description": "Capture scope change decisions and approvals.",
                "assistant_prompts": [
                    "Update the change log with recent scope decisions and approvals.",
                    "Verify approvals, impacts, and dates are documented.",
                    "Recommend next steps to communicate recent changes.",
                ],
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

from __future__ import annotations

from template_models import (
    DocumentTemplateDefaults,
    DocumentTemplatePayload,
    SpreadsheetSeedRow,
    SpreadsheetTemplateColumn,
    SpreadsheetTemplatePayload,
    Template,
    TemplateSummary,
    TemplateType,
)

TEMPLATES: list[Template] = [
    Template(
        template_id="project-charter",
        name="Project Charter",
        type=TemplateType.document,
        description="Define the purpose, scope, and stakeholders for a new project.",
        tags=["charter", "planning", "governance"],
        version="1.1",
        available_versions=["1.0", "1.1"],
        defaults=DocumentTemplateDefaults(classification="internal", retention_days=365),
        payload=DocumentTemplatePayload(
            name_template="{{project_id}} Project Charter",
            content_template=(
                "Project {{project_id}} charter for tenant {{tenant_id}}.\n"
                "Prepared by {{user}} on {{date}}.\n\n"
                "Objectives:\n- ...\n\nScope:\n- ...\n"
            ),
            metadata_template={"owner": "{{user}}", "project": "{{project_id}}"},
        ),
    ),
    Template(
        template_id="status-report",
        name="Status Report",
        type=TemplateType.document,
        description="Provide a weekly snapshot of progress, risks, and next steps.",
        tags=["status", "reporting"],
        version="1.0",
        available_versions=["1.0"],
        defaults=DocumentTemplateDefaults(classification="internal", retention_days=180),
        payload=DocumentTemplatePayload(
            name_template="{{project_id}} Status Report - {{date}}",
            content_template=(
                "Status report for {{project_id}} ({{date}}).\n"
                "Owner: {{user}}\n\n"
                "Highlights:\n- ...\n\nRisks:\n- ...\n"
            ),
        ),
    ),
    Template(
        template_id="raid-summary",
        name="RAID Summary",
        type=TemplateType.document,
        description="Summarize risks, assumptions, issues, and dependencies.",
        tags=["raid", "risk"],
        version="1.0",
        available_versions=["1.0"],
        defaults=DocumentTemplateDefaults(classification="confidential", retention_days=365),
        payload=DocumentTemplatePayload(
            name_template="{{project_id}} RAID Summary",
            content_template=(
                "RAID summary for {{project_id}} as of {{date}}.\n\n"
                "Risks:\n- ...\n\nAssumptions:\n- ...\n\nIssues:\n- ...\n\nDependencies:\n- ...\n"
            ),
            metadata_template={"prepared_for": "{{tenant_id}}"},
        ),
    ),
    Template(
        template_id="change-request",
        name="Change Request",
        type=TemplateType.document,
        description="Capture requested changes and impact assessment.",
        tags=["change", "governance"],
        version="1.0",
        available_versions=["1.0"],
        defaults=DocumentTemplateDefaults(classification="restricted", retention_days=365),
        payload=DocumentTemplatePayload(
            name_template="{{project_id}} Change Request",
            content_template=(
                "Change request for {{project_id}}.\n"
                "Submitted by {{user}} on {{date}}.\n\n"
                "Description:\n- ...\n\nImpact:\n- ...\n"
            ),
        ),
    ),
    Template(
        template_id="risk-register",
        name="Risk Register",
        type=TemplateType.spreadsheet,
        description="Track project risks with owners and mitigation strategies.",
        tags=["risk", "register"],
        version="1.0",
        available_versions=["1.0"],
        payload=SpreadsheetTemplatePayload(
            sheet_name_template="{{project_id}} Risk Register",
            columns=[
                SpreadsheetTemplateColumn(name="Risk", type="text", required=True),
                SpreadsheetTemplateColumn(name="Impact", type="text", required=True),
                SpreadsheetTemplateColumn(name="Likelihood", type="text", required=True),
                SpreadsheetTemplateColumn(name="Mitigation", type="text"),
                SpreadsheetTemplateColumn(name="Owner", type="text"),
            ],
            seed_rows=[
                SpreadsheetSeedRow(
                    values={
                        "Risk": "Supplier delay",
                        "Impact": "Schedule slip",
                        "Likelihood": "Medium",
                        "Mitigation": "Identify backup suppliers",
                        "Owner": "{{user}}",
                    }
                )
            ],
        ),
    ),
    Template(
        template_id="action-log",
        name="Action Log",
        type=TemplateType.spreadsheet,
        description="Capture and track action items across the team.",
        tags=["actions", "tasks"],
        version="1.0",
        available_versions=["1.0"],
        payload=SpreadsheetTemplatePayload(
            sheet_name_template="{{project_id}} Action Log",
            columns=[
                SpreadsheetTemplateColumn(name="Action", type="text", required=True),
                SpreadsheetTemplateColumn(name="Owner", type="text", required=True),
                SpreadsheetTemplateColumn(name="Due Date", type="date"),
                SpreadsheetTemplateColumn(name="Status", type="text"),
            ],
            seed_rows=[
                SpreadsheetSeedRow(
                    values={
                        "Action": "Kickoff meeting scheduled",
                        "Owner": "{{user}}",
                        "Due Date": "{{date}}",
                        "Status": "Planned",
                    }
                )
            ],
        ),
    ),
    Template(
        template_id="stakeholder-register",
        name="Stakeholder Register",
        type=TemplateType.spreadsheet,
        description="Document stakeholders and engagement notes.",
        tags=["stakeholders", "register"],
        version="1.0",
        available_versions=["1.0"],
        payload=SpreadsheetTemplatePayload(
            sheet_name_template="{{project_id}} Stakeholder Register",
            columns=[
                SpreadsheetTemplateColumn(name="Stakeholder", type="text", required=True),
                SpreadsheetTemplateColumn(name="Role", type="text"),
                SpreadsheetTemplateColumn(name="Influence", type="text"),
                SpreadsheetTemplateColumn(name="Interest", type="text"),
                SpreadsheetTemplateColumn(name="Notes", type="text"),
            ],
        ),
    ),
    Template(
        template_id="benefits-register",
        name="Benefits Register",
        type=TemplateType.spreadsheet,
        description="Track expected benefits and realization progress.",
        tags=["benefits", "register"],
        version="1.0",
        available_versions=["1.0"],
        payload=SpreadsheetTemplatePayload(
            sheet_name_template="{{project_id}} Benefits Register",
            columns=[
                SpreadsheetTemplateColumn(name="Benefit", type="text", required=True),
                SpreadsheetTemplateColumn(name="Owner", type="text"),
                SpreadsheetTemplateColumn(name="Target Value", type="number"),
                SpreadsheetTemplateColumn(name="Target Date", type="date"),
                SpreadsheetTemplateColumn(name="Status", type="text"),
            ],
        ),
    ),
]


def list_templates(
    *,
    template_type: TemplateType | None = None,
    tag: str | None = None,
    query: str | None = None,
) -> list[TemplateSummary]:
    results = TEMPLATES
    if template_type is not None:
        results = [item for item in results if item.type == template_type]
    if tag:
        lowered = tag.strip().lower()
        results = [
            item
            for item in results
            if any(t.lower() == lowered for t in item.tags)
        ]
    if query:
        lowered = query.strip().lower()
        results = [
            item
            for item in results
            if lowered in item.name.lower()
            or lowered in item.description.lower()
            or any(lowered in t.lower() for t in item.tags)
        ]
    return [item.summary() for item in results]


def get_template(template_id: str) -> Template | None:
    for item in TEMPLATES:
        if item.template_id == template_id:
            return item
    return None

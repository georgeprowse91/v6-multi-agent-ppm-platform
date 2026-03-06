"""add enum constraints for classification and status

Revision ID: 0004_add_enum_constraints
Revises: 0003_create_missing_tables
Create Date: 2025-02-15 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0004_add_enum_constraints"
down_revision = "0003_create_missing_tables"
branch_labels = None
depends_on = None

CLASSIFICATION_ENUM = ("public", "internal", "confidential", "restricted")
STATUS_ENUMS = {
    "budgets": ("draft", "approved", "committed"),
    "documents": ("draft", "review", "approved", "archived"),
    "issues": ("open", "in_progress", "resolved", "closed"),
    "portfolios": ("planning", "active", "archived"),
    "programs": ("planning", "active", "closed"),
    "projects": ("initiated", "planning", "execution", "monitoring", "closed"),
    "resources": ("active", "inactive", "on_leave"),
    "risks": ("open", "mitigated", "closed"),
    "vendors": ("active", "inactive", "pending"),
    "work_items": ("todo", "in_progress", "done", "blocked"),
}


def _enum_constraint(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    for table in (
        "portfolios",
        "programs",
        "projects",
        "budgets",
        "work_items",
        "risks",
        "issues",
        "vendors",
        "documents",
        "audit_events",
    ):
        with op.batch_alter_table(table) as batch_op:
            batch_op.create_check_constraint(
                f"ck_{table}_classification_enum",
                _enum_constraint("classification", CLASSIFICATION_ENUM),
            )

    for table, values in STATUS_ENUMS.items():
        with op.batch_alter_table(table) as batch_op:
            batch_op.create_check_constraint(
                f"ck_{table}_status_enum",
                _enum_constraint("status", values),
            )


def downgrade() -> None:
    for table in (
        "audit_events",
        "documents",
        "vendors",
        "issues",
        "risks",
        "work_items",
        "budgets",
        "projects",
        "programs",
        "portfolios",
    ):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(
                f"ck_{table}_classification_enum",
                type_="check",
            )

    for table in reversed(list(STATUS_ENUMS.keys())):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(
                f"ck_{table}_status_enum",
                type_="check",
            )

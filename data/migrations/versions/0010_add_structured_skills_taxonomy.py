"""add structured skills taxonomy columns to resource entities

Extends resource records with structured skill objects (category,
proficiency level, framework reference) and HR system linkage fields.

Revision ID: 0010_add_structured_skills_taxonomy
Revises: 0009_create_schema_registry_tables
Create Date: 2026-03-07 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_add_structured_skills_taxonomy"
down_revision = "0009_create_schema_registry_tables"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Create structured_skills table for normalised skill storage
    if not _table_exists("resource_skills"):
        op.create_table(
            "resource_skills",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("resource_id", sa.String(length=64), nullable=False),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("skill_id", sa.String(length=128), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column(
                "category",
                sa.String(length=32),
                nullable=False,
                comment="technical|leadership|domain|methodology|tool|language|certification|soft_skill",
            ),
            sa.Column(
                "proficiency_level",
                sa.Integer(),
                nullable=False,
                comment="1=Beginner, 2=Intermediate, 3=Advanced, 4=Expert, 5=Thought Leader",
            ),
            sa.Column(
                "framework",
                sa.String(length=16),
                nullable=True,
                comment="SFIA|ESCO|ONET|custom",
            ),
            sa.Column("framework_code", sa.String(length=64), nullable=True),
            sa.Column("years_experience", sa.Float(), nullable=True),
            sa.Column("last_assessed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "source",
                sa.String(length=32),
                nullable=True,
                comment="self_reported|manager_assessed|hr_system|certification|training_completion|ai_inferred",
            ),
            sa.Column("verified", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "idx_resource_skills_resource_id",
            "resource_skills",
            ["resource_id"],
        )
        op.create_index(
            "idx_resource_skills_tenant_skill",
            "resource_skills",
            ["tenant_id", "skill_id"],
        )
        op.create_index(
            "idx_resource_skills_category",
            "resource_skills",
            ["category"],
        )
        op.create_index(
            "idx_resource_skills_framework",
            "resource_skills",
            ["framework", "framework_code"],
        )

    # Create skills taxonomy reference table
    if not _table_exists("skills_taxonomy"):
        op.create_table(
            "skills_taxonomy",
            sa.Column("skill_id", sa.String(length=128), primary_key=True),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("category", sa.String(length=32), nullable=False),
            sa.Column("framework", sa.String(length=16), nullable=False),
            sa.Column("framework_code", sa.String(length=64), nullable=True),
            sa.Column("parent_skill_id", sa.String(length=128), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("aliases", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "idx_skills_taxonomy_category",
            "skills_taxonomy",
            ["category"],
        )
        op.create_index(
            "idx_skills_taxonomy_framework",
            "skills_taxonomy",
            ["framework", "framework_code"],
        )

    # Create portfolio demand tracking table
    if not _table_exists("portfolio_skill_demand"):
        op.create_table(
            "portfolio_skill_demand",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("portfolio_id", sa.String(length=64), nullable=False),
            sa.Column("project_id", sa.String(length=64), nullable=True),
            sa.Column("skill_id", sa.String(length=128), nullable=False),
            sa.Column("role", sa.String(length=128), nullable=True),
            sa.Column("required_proficiency", sa.Integer(), nullable=False),
            sa.Column("headcount", sa.Float(), nullable=False),
            sa.Column("hours_per_week", sa.Float(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("priority", sa.String(length=16), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "idx_portfolio_demand_tenant_portfolio",
            "portfolio_skill_demand",
            ["tenant_id", "portfolio_id"],
        )
        op.create_index(
            "idx_portfolio_demand_skill",
            "portfolio_skill_demand",
            ["skill_id"],
        )

    # Add HR linkage columns to canonical_entities if resource records are stored there
    if _table_exists("canonical_entities"):
        if not _column_exists("canonical_entities", "hr_system_id"):
            op.add_column(
                "canonical_entities",
                sa.Column("hr_system_id", sa.String(length=128), nullable=True),
            )
        if not _column_exists("canonical_entities", "hr_system_source"):
            op.add_column(
                "canonical_entities",
                sa.Column("hr_system_source", sa.String(length=32), nullable=True),
            )


def downgrade() -> None:
    if _table_exists("portfolio_skill_demand"):
        op.drop_table("portfolio_skill_demand")
    if _table_exists("skills_taxonomy"):
        op.drop_table("skills_taxonomy")
    if _table_exists("resource_skills"):
        op.drop_table("resource_skills")
    if _table_exists("canonical_entities"):
        if _column_exists("canonical_entities", "hr_system_source"):
            op.drop_column("canonical_entities", "hr_system_source")
        if _column_exists("canonical_entities", "hr_system_id"):
            op.drop_column("canonical_entities", "hr_system_id")

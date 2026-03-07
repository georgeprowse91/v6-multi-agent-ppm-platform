"""add methodology definitions table with tenant scoping and versioning

Stores organisational methodology definitions as tenant-scoped, versioned
records. Supports policy enforcement (allowed methodologies per tenant)
and change impact analysis.

Revision ID: 0011_add_methodology_definitions
Revises: 0010_add_structured_skills_taxonomy
Create Date: 2026-03-07 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_add_methodology_definitions"
down_revision = "0010_add_structured_skills_taxonomy"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("methodology_definitions"):
        op.create_table(
            "methodology_definitions",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("methodology_id", sa.String(length=128), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "type",
                sa.String(length=32),
                nullable=False,
                comment="predictive|adaptive|hybrid|custom",
            ),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="draft",
                comment="draft|published|deprecated|archived",
            ),
            sa.Column(
                "is_default",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("allowed_departments", sa.JSON(), nullable=True),
            sa.Column("stages", sa.JSON(), nullable=False),
            sa.Column("gates", sa.JSON(), nullable=True),
            sa.Column("monitoring", sa.JSON(), nullable=True),
            sa.Column("navigation_nodes", sa.JSON(), nullable=True),
            sa.Column("created_by", sa.String(length=128), nullable=True),
            sa.Column("published_by", sa.String(length=128), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=True),
        )
        op.create_index(
            "idx_methodology_defs_tenant",
            "methodology_definitions",
            ["tenant_id"],
        )
        op.create_index(
            "idx_methodology_defs_tenant_methodology",
            "methodology_definitions",
            ["tenant_id", "methodology_id"],
        )
        op.create_index(
            "idx_methodology_defs_tenant_status",
            "methodology_definitions",
            ["tenant_id", "status"],
        )
        op.create_index(
            "idx_methodology_defs_tenant_version",
            "methodology_definitions",
            ["tenant_id", "methodology_id", "version"],
            unique=True,
        )

    if not _table_exists("methodology_policies"):
        op.create_table(
            "methodology_policies",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False, unique=True),
            sa.Column(
                "allowed_methodology_ids",
                sa.JSON(),
                nullable=True,
                comment="List of methodology_ids this tenant may use; null means all",
            ),
            sa.Column(
                "default_methodology_id",
                sa.String(length=128),
                nullable=True,
            ),
            sa.Column("department_overrides", sa.JSON(), nullable=True),
            sa.Column("enforce_published_only", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "idx_methodology_policies_tenant",
            "methodology_policies",
            ["tenant_id"],
        )


def downgrade() -> None:
    if _table_exists("methodology_policies"):
        op.drop_table("methodology_policies")
    if _table_exists("methodology_definitions"):
        op.drop_table("methodology_definitions")

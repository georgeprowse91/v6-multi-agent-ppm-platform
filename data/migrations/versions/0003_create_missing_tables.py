"""create demand, resource, roi, and agent config tables

Revision ID: 0003_create_missing_tables
Revises: 0002_create_orchestration_states
Create Date: 2025-02-15 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_create_missing_tables"
down_revision = "0002_create_orchestration_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "demands",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("business_objective", sa.Text(), nullable=False),
        sa.Column("requester", sa.String(length=255), nullable=True),
        sa.Column("business_unit", sa.String(length=255), nullable=True),
        sa.Column("urgency", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "resources",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_table(
        "rois",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("roi", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "agent_configs",
        sa.Column("tenant_id", sa.String(length=64), primary_key=True),
        sa.Column("agents", sa.JSON(), nullable=False),
        sa.Column("project_configs", sa.JSON(), nullable=False),
        sa.Column("dev_users", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("agent_configs")
    op.drop_table("rois")
    op.drop_table("resources")
    op.drop_table("demands")

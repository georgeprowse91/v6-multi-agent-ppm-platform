"""create workflow engine tables

Revision ID: 0005_create_workflow_engine_tables
Revises: 0004_add_enum_constraints
Create Date: 2025-02-14 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_create_workflow_engine_tables"
down_revision = "0004_add_enum_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=512)),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tenant_id", "workflow_id"),
    )
    op.create_index(
        "ix_workflow_definitions_tenant_id",
        "workflow_definitions",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "workflow_instances",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("instance_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tenant_id", "instance_id"),
    )
    op.create_index(
        "ix_workflow_instances_tenant_id",
        "workflow_instances",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "workflow_tasks",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("instance_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("task_type", sa.String(length=64)),
        sa.Column("assignee", sa.String(length=128)),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tenant_id", "task_id"),
    )
    op.create_index(
        "ix_workflow_tasks_tenant_id",
        "workflow_tasks",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "workflow_events",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tenant_id", "event_id"),
    )

    op.create_table(
        "workflow_event_subscriptions",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("subscription_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64)),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tenant_id", "subscription_id"),
    )
    op.create_index(
        "ix_workflow_event_subscriptions_tenant_id",
        "workflow_event_subscriptions",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_event_subscriptions_tenant_id", table_name="workflow_event_subscriptions")
    op.drop_table("workflow_event_subscriptions")
    op.drop_table("workflow_events")
    op.drop_index("ix_workflow_tasks_tenant_id", table_name="workflow_tasks")
    op.drop_table("workflow_tasks")
    op.drop_index("ix_workflow_instances_tenant_id", table_name="workflow_instances")
    op.drop_table("workflow_instances")
    op.drop_index("ix_workflow_definitions_tenant_id", table_name="workflow_definitions")
    op.drop_table("workflow_definitions")

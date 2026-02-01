"""add idempotency key to workflow instances

Revision ID: 0007_add_idempotency_key_to_workflow_instances
Revises: 0006_add_integration_config_tables
Create Date: 2025-02-14 00:00:01.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_add_idempotency_key_to_workflow_instances"
down_revision = "0006_add_integration_config_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workflow_instances") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch_op.create_unique_constraint(
            "uq_workflow_instances_idempotency_key",
            ["idempotency_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("workflow_instances") as batch_op:
        batch_op.drop_constraint(
            "uq_workflow_instances_idempotency_key",
            type_="unique",
        )
        batch_op.drop_column("idempotency_key")

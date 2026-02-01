"""add schema name/version index for entities

Revision ID: 0008_add_entities_schema_version_index
Revises: 0007_add_idempotency_key_to_workflow_instances
Create Date: 2025-02-15 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0008_add_entities_schema_version_index"
down_revision = "0007_add_idempotency_key_to_workflow_instances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_entities_schema_version",
        "canonical_entities",
        ["schema_name", "schema_version"],
    )


def downgrade() -> None:
    op.drop_index("idx_entities_schema_version", table_name="canonical_entities")

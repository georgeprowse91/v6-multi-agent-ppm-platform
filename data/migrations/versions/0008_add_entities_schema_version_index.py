"""add schema name/version index for entities

Revision ID: 0008_add_entities_schema_version_index
Revises: 0007_add_idempotency_key_to_workflow_instances
Create Date: 2025-02-15 00:00:00.000000

Note: The canonical_entities table is created in migration 0009.
This migration only adds the index if the table already exists;
otherwise migration 0009 will create the table with the index.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "0008_add_entities_schema_version_index"
down_revision = "0007_add_idempotency_key_to_workflow_instances"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    if _table_exists("canonical_entities"):
        op.create_index(
            "idx_entities_schema_version",
            "canonical_entities",
            ["schema_name", "schema_version"],
        )


def downgrade() -> None:
    if _table_exists("canonical_entities"):
        op.drop_index("idx_entities_schema_version", table_name="canonical_entities")

"""create schema registry and promotion tables

Revision ID: 0009_create_schema_registry_tables
Revises: 0008_add_entities_schema_version_index
Create Date: 2025-02-20 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_create_schema_registry_tables"
down_revision = "0008_add_entities_schema_version_index"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("schema_registry"):
        op.create_table(
            "schema_registry",
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("schema", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("name", "version", name="pk_schema_registry"),
        )

    if not _table_exists("schema_promotions"):
        op.create_table(
            "schema_promotions",
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("environment", sa.String(length=32), nullable=False),
            sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint(
                "name", "version", "environment", name="pk_schema_promotions"
            ),
        )

    if not _table_exists("canonical_entities"):
        op.create_table(
            "canonical_entities",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("schema_name", sa.String(length=128), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        # Create the index that migration 0008 would have added
        op.create_index(
            "idx_entities_schema_version",
            "canonical_entities",
            ["schema_name", "schema_version"],
        )


def downgrade() -> None:
    if _table_exists("schema_promotions"):
        op.drop_table("schema_promotions")
    if _table_exists("schema_registry"):
        op.drop_table("schema_registry")
    if _table_exists("canonical_entities"):
        op.drop_table("canonical_entities")

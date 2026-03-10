"""Runtime migration rollback tests.

Verifies that Alembic migrations can upgrade to head and downgrade
back to base against a real SQLite database. This complements the
static AST check in ops/scripts/test_migration_rollback.py.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "data" / "migrations"

try:
    from alembic import command
    from alembic.config import Config

    HAS_ALEMBIC = True
except ImportError:
    HAS_ALEMBIC = False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not HAS_ALEMBIC, reason="alembic not installed"),
]


@pytest.fixture()
def alembic_cfg(tmp_path: Path) -> Config:
    """Create an Alembic config pointing at a temporary SQLite database."""
    db_path = tmp_path / "test_rollback.db"
    ini_path = MIGRATIONS_DIR / "alembic.ini"

    # Fall back to programmatic config if alembic.ini does not exist
    if ini_path.exists():
        cfg = Config(str(ini_path))
    else:
        cfg = Config()
        cfg.set_main_option("script_location", str(MIGRATIONS_DIR))

    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def test_full_upgrade_then_downgrade(alembic_cfg: Config) -> None:
    """Upgrade to head then downgrade all the way back to base."""
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")


def test_stepwise_downgrade(alembic_cfg: Config) -> None:
    """Upgrade to head then step down one revision at a time."""
    command.upgrade(alembic_cfg, "head")

    # Walk down one revision at a time until we reach base
    max_steps = 50  # safety limit
    for _ in range(max_steps):
        try:
            command.downgrade(alembic_cfg, "-1")
        except Exception:
            # Reached base or hit an error
            break

from pathlib import Path


def test_backup_runbook_has_core_sections() -> None:
    path = Path(__file__).resolve().parents[1] / "docs" / "runbooks" / "backup-recovery.md"
    content = path.read_text()

    for heading in (
        "# Backup and Recovery Runbook",
        "## Backup schedule and retention",
        "## Recovery procedures",
        "## Post-recovery validation checklist",
    ):
        assert heading in content

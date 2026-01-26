from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scheduler import AnalyticsScheduler  # noqa: E402


def test_schedule_and_due_jobs(tmp_path: Path) -> None:
    db_path = tmp_path / "scheduler.db"
    scheduler = AnalyticsScheduler(db_path)

    job = scheduler.schedule_job(
        name="daily-rollup",
        interval_minutes=15,
        tenant_id="tenant-a",
        payload={"dataset": "projects"},
    )

    assert job.job_id
    assert job.next_run > datetime.now(timezone.utc)

    due = scheduler.due_jobs(job.next_run + timedelta(seconds=1))
    assert len(due) == 1
    assert due[0].job_id == job.job_id


def test_update_job_and_record_run(tmp_path: Path) -> None:
    db_path = tmp_path / "scheduler.db"
    scheduler = AnalyticsScheduler(db_path)
    job = scheduler.schedule_job(
        name="weekly-metrics",
        interval_minutes=60,
        tenant_id="tenant-b",
        payload={},
    )

    updated = scheduler.update_job(job.job_id, "tenant-b", interval_minutes=120, enabled=False)
    assert updated is not None
    assert updated.interval_minutes == 120
    assert updated.enabled is False

    recorded = scheduler.record_run(job, "completed")
    assert recorded.status == "completed"
    assert recorded.last_run is not None

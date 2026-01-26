from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from audit_storage import AuditRetentionPolicy, LocalEncryptedWORMStorage  # noqa: E402
from retention_job import run_retention_enforcement  # noqa: E402


def test_retention_job_prunes_expired(tmp_path, monkeypatch) -> None:
    storage = LocalEncryptedWORMStorage(
        root=tmp_path, encryption_key="Y2hhbmdlLW1lLW5vdC1wcm9kLWsxMjM0NTY3ODkwMTIzNDU2Nzg5MA=="
    )
    policy = AuditRetentionPolicy(policy_id="internal-1y", duration_days=0)
    payload = {
        "id": "evt-expired",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": "tenant-alpha",
        "actor": {"id": "user-1"},
        "action": "test",
        "resource": {"id": "res-1"},
        "outcome": "success",
        "classification": "internal",
    }
    storage.persist_event("evt-expired", payload, policy)

    monkeypatch.setenv("AUDIT_WORM_LOCAL_PATH", str(tmp_path))
    monkeypatch.setenv(
        "AUDIT_LOG_ENCRYPTION_KEY", "Y2hhbmdlLW1lLW5vdC1wcm9kLWsxMjM0NTY3ODkwMTIzNDU2Nzg5MA=="
    )

    deleted = run_retention_enforcement(now=datetime.now(timezone.utc) + timedelta(days=1))

    assert deleted == 1
    assert not list(Path(tmp_path).glob("*.enc"))

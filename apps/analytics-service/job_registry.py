from pathlib import Path

JOB_MANIFEST_DIR = Path(__file__).resolve().parent / "jobs" / "manifests"


def list_job_manifests() -> list[Path]:
    return sorted(JOB_MANIFEST_DIR.glob("*.yaml"))

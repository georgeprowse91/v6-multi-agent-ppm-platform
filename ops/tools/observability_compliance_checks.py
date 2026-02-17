from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APPS_ROOT = REPO_ROOT / "apps"
REQUIRED_IMPORT_TOKENS = (
    "RequestMetricsMiddleware",
    "configure_metrics",
    "TraceMiddleware",
    "configure_tracing",
)
REQUIRED_MOUNT_LINES = (
    "configure_tracing(",
    "configure_metrics(",
    "app.add_middleware(TraceMiddleware",
    "app.add_middleware(RequestMetricsMiddleware",
)


@dataclass(frozen=True)
class ObservabilityViolation:
    check: str
    service: str
    message: str
    file_path: Path


def discover_service_main_files() -> dict[str, Path]:
    service_files: dict[str, Path] = {}
    for path in sorted(APPS_ROOT.glob("*/src/main.py")):
        service_files[path.parent.parent.name] = path
    return service_files


def check_service_observability_compliance() -> list[ObservabilityViolation]:
    violations: list[ObservabilityViolation] = []
    for service, main_file in discover_service_main_files().items():
        source = main_file.read_text()
        for line in REQUIRED_IMPORT_TOKENS:
            if line not in source:
                violations.append(
                    ObservabilityViolation(
                        check="imports",
                        service=service,
                        message=f"missing observability import: {line}",
                        file_path=main_file,
                    )
                )
        for token in REQUIRED_MOUNT_LINES:
            if token not in source:
                violations.append(
                    ObservabilityViolation(
                        check="middleware",
                        service=service,
                        message=f"missing observability mount: {token}",
                        file_path=main_file,
                    )
                )
    return violations


def format_violations(violations: list[ObservabilityViolation]) -> str:
    lines = ["Observability compliance checks failed:"]
    for violation in violations:
        rel_path = violation.file_path.relative_to(REPO_ROOT)
        lines.append(f" - [{violation.check}] {violation.service}: {violation.message} ({rel_path})")
    return "\n".join(lines)

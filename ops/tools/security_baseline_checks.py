from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICES_ROOT = REPO_ROOT / "services"
REQUIRED_AUTH_EXEMPT_PATHS = {'"/health"', '"/healthz"', '"/version"'}
AUTH_MIDDLEWARE_EXEMPT_SERVICES = {"agent-runtime", "auth-service", "identity-access"}
SECRET_ENV_PATTERN = re.compile(r"(SECRET|TOKEN|PASSWORD|KEY|CONNECTION_STRING|WEBHOOK)")


@dataclass(frozen=True)
class BaselineViolation:
    check: str
    service: str
    message: str
    file_path: Path


def discover_service_main_files() -> dict[str, Path]:
    service_files: dict[str, Path] = {}
    for path in sorted(SERVICES_ROOT.glob("*/src/main.py")):
        service_files[path.parent.parent.name] = path
    return service_files


def _exempt_paths_set(text: str) -> set[str]:
    """Extract exempt_paths values from a (possibly multi-line) text block."""
    if "exempt_paths" not in text:
        return set()
    literal = text.split("exempt_paths=", 1)[1]
    match = re.search(r"\{([^}]*)\}", literal)
    if not match:
        return set()
    values = set()
    for token in match.group(1).split(","):
        token = token.strip()
        if token:
            values.add(token)
    return values


def _has_auth_middleware(source: str) -> bool:
    """Check if source registers AuthTenantMiddleware (single or multi-line)."""
    if "app.add_middleware(AuthTenantMiddleware" in source:
        return True
    # Handle multi-line: app.add_middleware(\n    AuthTenantMiddleware, ...
    if "app.add_middleware(\n" in source and "AuthTenantMiddleware" in source:
        return True
    return False


def _extract_auth_middleware_block(source: str) -> str | None:
    """Return the full text block of the AuthTenantMiddleware add_middleware call."""
    # Try single-line match first
    match = re.search(
        r"app\.add_middleware\(AuthTenantMiddleware[^)]*\)", source
    )
    if match:
        return match.group(0)
    # Try multi-line match
    match = re.search(
        r"app\.add_middleware\(\s*AuthTenantMiddleware[^)]*\)", source, re.DOTALL
    )
    if match:
        return match.group(0)
    return None


def check_service_security_middleware() -> list[BaselineViolation]:
    violations: list[BaselineViolation] = []
    for service, main_file in discover_service_main_files().items():
        source = main_file.read_text()
        if "apply_api_governance(app" not in source:
            violations.append(
                BaselineViolation(
                    check="middleware",
                    service=service,
                    message="missing apply_api_governance(app, service_name=...)",
                    file_path=main_file,
                )
            )
        for middleware_token in ("TraceMiddleware", "RequestMetricsMiddleware"):
            if f"app.add_middleware({middleware_token}" not in source:
                violations.append(
                    BaselineViolation(
                        check="middleware",
                        service=service,
                        message=f"missing {middleware_token}",
                        file_path=main_file,
                    )
                )

        if service in AUTH_MIDDLEWARE_EXEMPT_SERVICES:
            continue
        if not _has_auth_middleware(source):
            violations.append(
                BaselineViolation(
                    check="auth_middleware",
                    service=service,
                    message="missing AuthTenantMiddleware registration",
                    file_path=main_file,
                )
            )
            continue
        auth_block = _extract_auth_middleware_block(source)
        exempt_paths = _exempt_paths_set(auth_block or "")
        if not REQUIRED_AUTH_EXEMPT_PATHS.issubset(exempt_paths):
            violations.append(
                BaselineViolation(
                    check="auth_exempt_paths",
                    service=service,
                    message=(
                        "AuthTenantMiddleware exempt_paths must include "
                        f"{sorted(REQUIRED_AUTH_EXEMPT_PATHS)}; found {sorted(exempt_paths)}"
                    ),
                    file_path=main_file,
                )
            )
    return violations


def check_secret_resolution_usage() -> list[BaselineViolation]:
    violations: list[BaselineViolation] = []
    for service, main_file in discover_service_main_files().items():
        lines = main_file.read_text().splitlines()
        for line_no, line in enumerate(lines, start=1):
            if "os.getenv(" not in line:
                continue
            env_match = re.search(r'os\.getenv\("([A-Z0-9_]+)"', line)
            if not env_match:
                continue
            env_name = env_match.group(1)
            if not SECRET_ENV_PATTERN.search(env_name):
                continue
            # Check same-line resolve_secret wrapping
            if "resolve_secret(os.getenv(" in line:
                continue
            # Check multi-line: resolve_secret( on a preceding line wrapping this os.getenv
            if line_no >= 2 and "resolve_secret(" in lines[line_no - 2]:
                continue
            violations.append(
                BaselineViolation(
                    check="secret_resolution",
                    service=service,
                    message=f"{env_name} is read without resolve_secret at line {line_no}",
                    file_path=main_file,
                )
            )
    return violations


def run_all_checks() -> list[BaselineViolation]:
    return [*check_service_security_middleware(), *check_secret_resolution_usage()]


def format_violations(violations: list[BaselineViolation]) -> str:
    lines = ["Security baseline checks failed:"]
    for violation in violations:
        lines.append(
            f" - [{violation.check}] {violation.service}: {violation.message} ({violation.file_path.relative_to(REPO_ROOT)})"
        )
    return "\n".join(lines)

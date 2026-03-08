from __future__ import annotations

from pathlib import Path

import pytest

from ops.tools.security_baseline_checks import (
    AUTH_MIDDLEWARE_EXEMPT_SERVICES,
    REQUIRED_AUTH_EXEMPT_PATHS,
    check_secret_resolution_usage,
    check_service_security_middleware,
    discover_service_main_files,
)


def _violations_by_service(check_name: str) -> dict[str, list[str]]:
    combined = [*check_service_security_middleware(), *check_secret_resolution_usage()]
    grouped: dict[str, list[str]] = {}
    for violation in combined:
        if violation.check != check_name:
            continue
        grouped.setdefault(violation.service, []).append(violation.message)
    return grouped


@pytest.mark.parametrize(
    ("service", "main_file"),
    sorted(discover_service_main_files().items(), key=lambda item: item[0]),
)
def test_service_has_required_security_middleware(service: str, main_file: Path) -> None:
    source = main_file.read_text()

    assert "apply_api_governance(app" in source
    assert "app.add_middleware(TraceMiddleware" in source
    assert "app.add_middleware(RequestMetricsMiddleware" in source

    if service in AUTH_MIDDLEWARE_EXEMPT_SERVICES:
        return

    assert "app.add_middleware(AuthTenantMiddleware" in source or (
        "app.add_middleware(\n" in source and "AuthTenantMiddleware" in source
    ), f"{service} missing AuthTenantMiddleware registration"

    # Verify all required exempt paths are present in the middleware call
    auth_lines = [
        line.strip()
        for line in source.splitlines()
        if "AuthTenantMiddleware" in line and "exempt_paths" in line
    ]
    if not auth_lines:
        # exempt_paths may span multiple lines; check full source
        assert all(
            path in source for path in REQUIRED_AUTH_EXEMPT_PATHS
        ), f"{service} missing required exempt paths {REQUIRED_AUTH_EXEMPT_PATHS}"
    else:
        for path in REQUIRED_AUTH_EXEMPT_PATHS:
            assert (
                path in auth_lines[0]
            ), f"{service} missing required exempt path {path} in AuthTenantMiddleware"


@pytest.mark.parametrize(
    "check_name",
    ["middleware", "auth_middleware", "auth_exempt_paths", "secret_resolution"],
)
def test_cross_service_baseline_checks_have_no_violations(check_name: str) -> None:
    violations = _violations_by_service(check_name)
    assert not violations, f"{check_name} violations: {violations}"

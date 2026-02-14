#!/usr/bin/env python3
"""Lightweight guardrail for UI coverage matrix completeness."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "docs" / "ui" / "UI_COVERAGE_MATRIX.md"

REQUIRED_CAPABILITIES = [
    "Capability 1: Initial login + session establishment",
    "Capability 2: Entry view after login with assistant-first launcher",
    "Capability 3: Create new project (all steps and post-create routing)",
    "Capability 4: Access existing portfolio workspace (list/search + open)",
    "Capability 5: Access existing program workspace (list/search + open)",
    "Capability 6: Access existing project workspace (list/search + open)",
    "Capability 7: Each subsequent screen for each of those 4 options (complete route coverage)",
    "Capability 8: Agent gallery (list, filter, open profile, capabilities, config, test, run)",
    "Capability 9: Connector registry (list/category/config/test/enable per project/certification)",
    "Capability 10: Methodology navigation (left index/map/detail/monitoring/dashboard)",
    "Capability 11: Configure user access (roles/permissions + UI RBAC enforcement)",
    "Capability 12: Performance dashboard (open/filter/drill-down/what-if/export pack)",
    "Capability 13: Generate files/artifacts (document/spreadsheet/timeline/dashboard; edit/review/approve/publish)",
    "Capability 14: Read/push records to Systems of Record (SoRs)",
    "Capability 15: Approval flows (stage gates/template/publish approvals + audit evidence)",
]

REQUIRED_ROUTE_MARKERS = [
    "/login",
    "/",
    "/intake/new",
    "/intake/status/:requestId",
    "/portfolios",
    "/programs",
    "/projects",
    "/projects/:projectId/config",
    "/marketplace/connectors",
    "/approvals",
    "/analytics/dashboard",
    "/admin/roles",
    "/admin/audit",
]

REQUIRED_FIELDS_PER_CAPABILITY = [
    "Entry routes:",
    "UI components:",
    "Backend endpoints used:",
    "Feature-flagged:",
    "Actual build:",
    "Demo-safe/demo-seeded:",
]


def _fail(message: str) -> None:
    raise SystemExit(f"ui_coverage_check FAILED: {message}")


def main() -> None:
    if not MATRIX_PATH.exists():
        _fail(f"missing matrix file: {MATRIX_PATH}")

    content = MATRIX_PATH.read_text(encoding="utf-8")

    missing_caps = [cap for cap in REQUIRED_CAPABILITIES if cap not in content]
    if missing_caps:
        _fail("missing capability sections: " + ", ".join(missing_caps))

    missing_routes = [route for route in REQUIRED_ROUTE_MARKERS if route not in content]
    if missing_routes:
        _fail("missing required route references: " + ", ".join(missing_routes))

    # Validate each capability block has required field labels.
    headings = list(re.finditer(r"^### Capability\s+\d+:.*$", content, flags=re.MULTILINE))
    if len(headings) < 15:
        _fail(f"expected at least 15 capability headings, found {len(headings)}")

    for idx, match in enumerate(headings):
        start = match.start()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(content)
        block = content[start:end]
        for field in REQUIRED_FIELDS_PER_CAPABILITY:
            if field not in block:
                _fail(f"{match.group(0)} is missing field '{field}'")

    print("ui_coverage_check PASSED")


if __name__ == "__main__":
    main()

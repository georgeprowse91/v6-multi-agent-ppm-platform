#!/usr/bin/env python3
"""Generate synthetic demo records that align with canonical demo entity shapes."""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from faker import Faker
except ImportError:  # Faker is optional; builtin generator fallback is used.
    Faker = None  # type: ignore[assignment]

TENANT_ID = "tenant-demo"
CLASSIFICATIONS = ["public", "internal", "confidential", "restricted"]
PROJECT_STATUSES = ["initiated", "planning", "execution", "monitoring", "closed"]
TASK_STATUSES = ["todo", "in_progress", "blocked", "done"]
RISK_STATUSES = ["open", "mitigated", "closed"]

TASK_TYPES = ["task", "milestone", "deliverable"]
RISK_LIKELIHOODS = ["rare", "unlikely", "possible", "likely"]
RISK_IMPACTS = ["low", "medium", "high", "critical"]
ISSUE_STATUSES = ["open", "in_progress", "resolved", "closed"]
ISSUE_SEVERITIES = ["low", "medium", "high", "critical"]
VENDOR_CATEGORIES = ["software", "services", "consulting", "hardware"]

MIN_RECORD_COUNTS = {
    "portfolios": 3,
    "programs": 5,
    "projects": 10,
    "tasks": 120,
    "risks": 40,
    "issues": 40,
    "vendors": 10,
    "contracts": 12,
    "approvals": 15,
    "notifications": 40,
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _iso_date(offset_days: int = 0) -> str:
    return (date.today() + timedelta(days=offset_days)).isoformat()


def _build_name_generator(seed: int) -> Any:
    random.seed(seed)
    if Faker:
        fake = Faker()
        fake.seed_instance(seed)
        return fake
    return None


def _pick_name(fake: Any) -> str:
    if fake:
        return fake.name()
    first = random.choice(["Alex", "Jordan", "Taylor", "Morgan", "Riley", "Casey", "Quinn"])
    last = random.choice(["Parker", "Nguyen", "Patel", "Singh", "Garcia", "Johnson", "Kim"])
    return f"{first} {last}"


def generate_dataset(size: int, seed: int) -> dict[str, list[dict[str, Any]]]:
    fake = _build_name_generator(seed)
    now = _iso_now()

    counts = {
        "portfolios": max(size, MIN_RECORD_COUNTS["portfolios"]),
        "programs": max(size, MIN_RECORD_COUNTS["programs"]),
        "projects": max(size * 2, MIN_RECORD_COUNTS["projects"]),
        "tasks": max(size * 12, MIN_RECORD_COUNTS["tasks"]),
        "resources": max(size * 3, 18),
        "budgets": max(size, 6),
        "epics": max(size * 3, 15),
        "sprints": max(size * 2, 10),
        "risks": max(size * 4, MIN_RECORD_COUNTS["risks"]),
        "issues": max(size * 4, MIN_RECORD_COUNTS["issues"]),
        "vendors": max(size, MIN_RECORD_COUNTS["vendors"]),
        "contracts": max(size * 2, MIN_RECORD_COUNTS["contracts"]),
        "policies": max(size, 6),
        "approvals": max(size * 2, MIN_RECORD_COUNTS["approvals"]),
        "notifications": max(size * 4, MIN_RECORD_COUNTS["notifications"]),
    }

    portfolios = [
        {
            "id": f"gen-portfolio-{i:03d}",
            "tenant_id": TENANT_ID,
            "name": f"Strategic Portfolio {i}",
            "status": "active",
            "owner": _pick_name(fake),
            "classification": random.choice(CLASSIFICATIONS),
            "kpi_delivery_on_time_target_pct": random.choice([85, 90, 95]),
            "target_npv": random.randint(400000, 2000000),
            "strategic_theme": random.choice(["growth", "efficiency", "resilience"]),
            "created_at": now,
        }
        for i in range(1, counts["portfolios"] + 1)
    ]

    programs = [
        {
            "id": f"gen-program-{i:03d}",
            "tenant_id": TENANT_ID,
            "portfolio_id": portfolios[(i - 1) % len(portfolios)]["id"],
            "name": f"Program {i}",
            "status": "active",
            "owner": _pick_name(fake),
            "classification": random.choice(CLASSIFICATIONS),
            "created_at": now,
        }
        for i in range(1, counts["programs"] + 1)
    ]

    projects = [
        {
            "id": f"gen-project-{i:03d}",
            "tenant_id": TENANT_ID,
            "program_id": programs[(i - 1) % len(programs)]["id"],
            "name": f"Project {i}",
            "status": random.choice(PROJECT_STATUSES),
            "health": random.choice(["green", "amber", "red"]),
            "owner": _pick_name(fake),
            "start_date": _iso_date(-30 - i),
            "end_date": _iso_date(120 + i),
            "classification": random.choice(CLASSIFICATIONS),
            "created_at": now,
        }
        for i in range(1, counts["projects"] + 1)
    ]

    tasks = [
        {
            "id": f"gen-task-{i:04d}",
            "tenant_id": TENANT_ID,
            "project_id": projects[(i - 1) % len(projects)]["id"],
            "title": f"Task {i}",
            "status": random.choice(TASK_STATUSES),
            "type": random.choice(TASK_TYPES),
            "assigned_to": f"gen-resource-{((i - 1) % counts['resources']) + 1:03d}",
            "story_points": random.choice([1, 2, 3, 5, 8]),
            "classification": random.choice(CLASSIFICATIONS),
            "created_at": now,
        }
        for i in range(1, counts["tasks"] + 1)
    ]

    resources = [
        {
            "id": f"gen-resource-{i:03d}",
            "tenant_id": TENANT_ID,
            "program_id": programs[(i - 1) % len(programs)]["id"],
            "name": _pick_name(fake),
            "role": random.choice(["Product Manager", "Engineer", "Architect", "Analyst"]),
            "cost_rate": random.randint(85, 225),
            "status": "active",
            "created_at": now,
        }
        for i in range(1, counts["resources"] + 1)
    ]

    budgets = [
        {
            "id": f"gen-budget-{i:03d}",
            "portfolio_id": portfolios[(i - 1) % len(portfolios)]["id"],
            "name": f"FY{date.today().year + 1} Portfolio Budget {i}",
            "amount": random.randint(250000, 1250000),
            "currency": random.choice(["AUD", "EUR", "GBP"]),
            "fiscal_year": date.today().year + 1,
            "status": "approved",
            "owner": _pick_name(fake),
            "classification": random.choice(CLASSIFICATIONS),
            "created_at": now,
        }
        for i in range(1, counts["budgets"] + 1)
    ]

    epics = [
        {
            "id": f"gen-epic-{i:03d}",
            "project_id": projects[(i - 1) % len(projects)]["id"],
            "title": f"Epic {i}",
            "status": random.choice(["proposed", "active", "done"]),
            "target_release": f"R{(i % 4) + 1}",
        }
        for i in range(1, counts["epics"] + 1)
    ]

    sprints = [
        {
            "id": f"gen-sprint-{i:03d}",
            "project_id": projects[(i - 1) % len(projects)]["id"],
            "name": f"Sprint {i}",
            "start_date": _iso_date(-14 + (i * 14)),
            "end_date": _iso_date(i * 14),
            "velocity_target": random.choice([20, 24, 28, 32]),
        }
        for i in range(1, counts["sprints"] + 1)
    ]

    risks = [
        {
            "id": f"gen-risk-{i:03d}",
            "tenant_id": TENANT_ID,
            "project_id": projects[(i - 1) % len(projects)]["id"],
            "owner": _pick_name(fake),
            "status": random.choice(RISK_STATUSES),
            "likelihood": random.choice(RISK_LIKELIHOODS),
            "impact": random.choice(RISK_IMPACTS),
            "mitigation": "Escalation and fallback plan documented.",
            "classification": random.choice(CLASSIFICATIONS),
            "created_at": now,
        }
        for i in range(1, counts["risks"] + 1)
    ]

    issues = [
        {
            "id": f"gen-issue-{i:03d}",
            "tenant_id": TENANT_ID,
            "project_id": projects[(i - 1) % len(projects)]["id"],
            "title": f"Issue {i}",
            "status": random.choice(ISSUE_STATUSES),
            "severity": random.choice(ISSUE_SEVERITIES),
            "owner": _pick_name(fake),
            "classification": random.choice(CLASSIFICATIONS),
            "created_at": now,
        }
        for i in range(1, counts["issues"] + 1)
    ]

    vendors = [
        {
            "id": f"gen-vendor-{i:03d}",
            "tenant_id": TENANT_ID,
            "name": f"Vendor {i}",
            "status": "active",
            "category": random.choice(VENDOR_CATEGORIES),
            "owner": _pick_name(fake),
            "rating": random.choice([3, 4, 5]),
            "classification": random.choice(CLASSIFICATIONS),
            "created_at": now,
        }
        for i in range(1, counts["vendors"] + 1)
    ]

    contracts = [
        {
            "id": f"gen-contract-{i:03d}",
            "name": f"Contract {i}",
            "vendor_id": vendors[(i - 1) % len(vendors)]["id"],
            "project_id": projects[(i - 1) % len(projects)]["id"],
            "value": random.randint(80000, 450000),
            "status": random.choice(["draft", "active", "expired"]),
            "start_date": _iso_date(-90),
            "end_date": _iso_date(365),
        }
        for i in range(1, counts["contracts"] + 1)
    ]

    policies = [
        {
            "id": f"gen-policy-{i:03d}",
            "title": f"Control Policy {i}",
            "framework": random.choice(["SOC2", "ISO27001", "NIST"]),
            "status": "active",
            "control_owner": _pick_name(fake),
            "effective_date": _iso_date(-120),
        }
        for i in range(1, counts["policies"] + 1)
    ]

    approvals = [
        {
            "id": f"gen-approval-{i:03d}",
            "entity_type": "budget" if i % 2 else "contract",
            "entity_id": budgets[(i - 1) % len(budgets)]["id"] if i % 2 else contracts[(i - 1) % len(contracts)]["id"],
            "requester": _pick_name(fake),
            "approver": _pick_name(fake),
            "status": random.choice(["pending", "approved", "rejected"]),
            "requested_at": now,
            "decision_at": now,
        }
        for i in range(1, counts["approvals"] + 1)
    ]

    notifications = [
        {
            "id": f"gen-notification-{i:03d}",
            "tenant_id": TENANT_ID,
            "workflow_id": f"wf-{i}",
            "type": random.choice(["approval", "risk", "status"]),
            "channel": random.choice(["email", "slack", "teams"]),
            "severity": random.choice(["info", "warning", "critical"]),
            "title": f"Notification {i}",
            "message": f"Automated notification {i} generated for demo workflow activity.",
            "read": False,
            "created_at": now,
        }
        for i in range(1, counts["notifications"] + 1)
    ]

    return {
        "portfolios": portfolios,
        "programs": programs,
        "projects": projects,
        "tasks": tasks,
        "resources": resources,
        "budgets": budgets,
        "epics": epics,
        "sprints": sprints,
        "risks": risks,
        "issues": issues,
        "vendors": vendors,
        "contracts": contracts,
        "policies": policies,
        "approvals": approvals,
        "notifications": notifications,
    }


def _merge_existing_rows(existing_rows: list[dict[str, Any]], generated_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not existing_rows:
        return generated_rows

    merged = list(existing_rows)
    existing_ids = {str(row.get("id")) for row in existing_rows if "id" in row}
    for row in generated_rows:
        if "id" in row and str(row["id"]) in existing_ids:
            continue
        merged.append(row)
    return merged


def write_dataset(dataset: dict[str, list[dict[str, Any]]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in dataset.items():
        path = output_dir / f"{name}.json"
        existing_rows: list[dict[str, Any]] = []
        if path.exists():
            existing_rows = json.loads(path.read_text(encoding="utf-8"))

        merged_rows = _merge_existing_rows(existing_rows, rows)
        path.write_text(json.dumps(merged_rows, indent=2), encoding="utf-8")


def write_manifest(dataset: dict[str, list[dict[str, Any]]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["entity_type", "record_count"])
        writer.writeheader()
        for entity, rows in sorted(dataset.items()):
            writer.writerow({"entity_type": entity, "record_count": len(rows)})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="data/demo", help="Directory for JSON entity files")
    parser.add_argument(
        "--manifest-path",
        default="data/seed/manifest.csv",
        help="CSV summary manifest path",
    )
    parser.add_argument("--size", type=int, default=10, help="Base dataset size multiplier")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for repeatability")
    args = parser.parse_args()

    dataset = generate_dataset(size=max(1, args.size), seed=args.seed)
    write_dataset(dataset, Path(args.output_dir))
    write_manifest(dataset, Path(args.manifest_path))
    print(f"Wrote generated demo data to {args.output_dir} and {args.manifest_path}")


if __name__ == "__main__":
    main()

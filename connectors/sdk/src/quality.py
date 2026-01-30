from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_QUALITY_ROOT = REPO_ROOT / "packages" / "data-quality" / "src"
if str(DATA_QUALITY_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_QUALITY_ROOT))

try:
    from data_quality.rules import evaluate_quality_rules
except ImportError:  # pragma: no cover - optional dependency
    evaluate_quality_rules = None


def evaluate_quality(record_type: str, record: dict[str, Any]) -> dict[str, Any] | None:
    if not evaluate_quality_rules:
        return None
    report = evaluate_quality_rules(record_type, record)
    if report.is_valid:
        return {
            "score": 1.0,
            "dimensions": {"completeness": 1.0},
            "rules_checked": [issue.rule_id for issue in report.issues],
            "issues": [issue.__dict__ for issue in report.issues],
        }
    score = max(0.0, 1.0 - (0.1 * len(report.issues)))
    return {
        "score": round(score, 4),
        "dimensions": {"completeness": max(0.0, 1.0 - (0.1 * len(report.issues)))},
        "rules_checked": [issue.rule_id for issue in report.issues],
        "issues": [issue.__dict__ for issue in report.issues],
    }

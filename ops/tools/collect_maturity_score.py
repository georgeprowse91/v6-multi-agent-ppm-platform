from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = REPO_ROOT / "ops" / "config" / "maturity_model.yaml"


@dataclass
class KpiResult:
    dimension: str
    id: str
    source: str
    value: float | None
    unit: str
    score: float
    status: str
    details: str


def _read_model(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def _json_path_get(payload: Any, path: str) -> Any:
    if not path.startswith("$."):
        raise ValueError(f"Unsupported path syntax: {path}")
    node = payload
    for token in path[2:].split("."):
        if not isinstance(node, dict) or token not in node:
            raise KeyError(token)
        node = node[token]
    return node


def _score_value(value: float, scoring: dict[str, Any]) -> float:
    direction = scoring["direction"]
    target = float(scoring["target"])
    floor = float(scoring["floor"])

    if direction == "higher_is_better":
        if target == floor:
            return 100.0 if value >= target else 0.0
        raw = (value - floor) / (target - floor)
    elif direction == "lower_is_better":
        if target == floor:
            return 100.0 if value <= target else 0.0
        raw = (floor - value) / (floor - target)
    else:
        raise ValueError(f"Unknown scoring direction: {direction}")
    return round(max(0.0, min(1.0, raw)) * 100.0, 2)


def _resolve_policy_thresholds(model: dict[str, Any], as_of: date) -> dict[str, float]:
    baseline = model["release_policy"]
    active = {
        "minimum_overall_score": float(baseline["minimum_overall_score"]),
        "minimum_dimension_score": float(baseline["minimum_dimension_score"]),
    }
    for entry in model.get("ratchet_policy", {}).get("schedule", []):
        effective_raw = entry["effective_date"]
        effective = effective_raw if isinstance(effective_raw, date) else date.fromisoformat(str(effective_raw))
        if as_of >= effective:
            active["minimum_overall_score"] = float(entry["minimum_overall_score"])
            active["minimum_dimension_score"] = float(entry["minimum_dimension_score"])
    return active


def collect_scores(model: dict[str, Any], artifact_root: Path) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    weights: dict[str, float] = model["weights"]
    kpi_results: list[KpiResult] = []

    for dimension, kpis in model["dimensions"].items():
        for kpi in kpis:
            source = (artifact_root / kpi["source"]).resolve()
            source_label = str(source.relative_to(REPO_ROOT)) if source.is_relative_to(REPO_ROOT) else str(source)
            if not source.exists():
                kpi_results.append(
                    KpiResult(
                        dimension=dimension,
                        id=kpi["id"],
                        source=source_label,
                        value=None,
                        unit=kpi["unit"],
                        score=0.0,
                        status="missing-artifact",
                        details="Artifact file missing",
                    )
                )
                continue
            try:
                payload = json.loads(source.read_text())
                raw_value = _json_path_get(payload, kpi["path"])
                value = float(raw_value)
                score = _score_value(value, kpi["scoring"])
                status = "pass" if score >= 100.0 else "warn"
                kpi_results.append(
                    KpiResult(
                        dimension=dimension,
                        id=kpi["id"],
                        source=source_label,
                        value=value,
                        unit=kpi["unit"],
                        score=score,
                        status=status,
                        details="",
                    )
                )
            except Exception as exc:  # noqa: BLE001
                kpi_results.append(
                    KpiResult(
                        dimension=dimension,
                        id=kpi["id"],
                        source=source_label,
                        value=None,
                        unit=kpi["unit"],
                        score=0.0,
                        status="parse-error",
                        details=str(exc),
                    )
                )

    dimension_scores: dict[str, float] = {}
    for dimension in model["dimensions"]:
        scoped = [item.score for item in kpi_results if item.dimension == dimension]
        dimension_scores[dimension] = round(sum(scoped) / len(scoped), 2) if scoped else 0.0

    overall = 0.0
    for dimension, weight in weights.items():
        overall += dimension_scores.get(dimension, 0.0) * float(weight)
    overall = round(overall, 2)

    today = datetime.now(timezone.utc).date()
    thresholds = _resolve_policy_thresholds(model, today)
    must_pass_dimensions = model["release_policy"].get("must_pass_dimensions", [])

    failed_dimensions = sorted(
        [
            name
            for name, score in dimension_scores.items()
            if score < thresholds["minimum_dimension_score"]
        ]
    )
    required_dimension_failures = sorted(
        [
            name
            for name in must_pass_dimensions
            if dimension_scores.get(name, 0.0) < thresholds["minimum_dimension_score"]
        ]
    )

    eligible = (
        overall >= thresholds["minimum_overall_score"]
        and not failed_dimensions
        and not required_dimension_failures
    )

    backlog = [
        {
            "dimension": name,
            "score": score,
            "focus": "Raise KPI scores above current ratchet threshold",
        }
        for name, score in sorted(dimension_scores.items(), key=lambda item: item[1])[:3]
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_root": str(artifact_root),
        "overall_score": overall,
        "dimension_scores": dimension_scores,
        "thresholds": thresholds,
        "release_eligible": eligible,
        "failed_dimensions": failed_dimensions,
        "required_dimension_failures": required_dimension_failures,
        "kpis": [item.__dict__ for item in kpi_results],
        "monthly_backlog": backlog,
    }


def _render_markdown(scorecard: dict[str, Any]) -> str:
    lines = [
        "# Maturity Scorecard Snapshot",
        "",
        f"- Generated at: `{scorecard['generated_at']}`",
        f"- Overall score: **{scorecard['overall_score']}**",
        f"- Release eligible: **{'yes' if scorecard['release_eligible'] else 'no'}**",
        f"- Active thresholds: overall ≥ {scorecard['thresholds']['minimum_overall_score']}, dimension ≥ {scorecard['thresholds']['minimum_dimension_score']}",
        "",
        "## Dimension scores",
        "",
        "| Dimension | Score |",
        "| --- | ---: |",
    ]
    for name, score in sorted(scorecard["dimension_scores"].items()):
        lines.append(f"| {name} | {score} |")

    lines.extend(
        [
            "",
            "## Monthly backlog (lowest scoring dimensions)",
            "",
            "| Rank | Dimension | Score | Focus |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for idx, item in enumerate(scorecard["monthly_backlog"], start=1):
        lines.append(f"| {idx} | {item['dimension']} | {item['score']} | {item['focus']} |")

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect maturity KPIs from CI artifacts")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--artifact-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT / "artifacts" / "maturity" / "scorecard-latest.json",
    )
    parser.add_argument(
        "--snapshot-md",
        type=Path,
        default=REPO_ROOT / "docs" / "production-readiness" / "maturity-scorecards" / "latest.md",
    )
    parser.add_argument(
        "--enforce-thresholds",
        action="store_true",
        help="Exit with non-zero status if release eligibility checks fail",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model = _read_model(args.model)
    scorecard = collect_scores(model, args.artifact_root)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(scorecard, indent=2) + "\n")

    args.snapshot_md.parent.mkdir(parents=True, exist_ok=True)
    args.snapshot_md.write_text(_render_markdown(scorecard))

    print(f"Wrote maturity scorecard JSON: {args.output_json}")
    print(f"Wrote maturity scorecard snapshot: {args.snapshot_md}")

    if args.enforce_thresholds and not scorecard["release_eligible"]:
        print("Maturity thresholds not met.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

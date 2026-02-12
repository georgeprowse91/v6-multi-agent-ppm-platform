from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Locust benchmark stats against baseline metrics."
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline JSON metrics.",
    )
    parser.add_argument(
        "--stats",
        type=Path,
        required=True,
        help="Path to Locust *_stats.csv file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Markdown output path for comparison results.",
    )
    parser.add_argument(
        "--threshold-pct",
        type=float,
        default=None,
        help="Override allowed degradation percentage for all benchmark groups.",
    )
    return parser.parse_args()


def load_baselines(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_stats(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return {row["Name"]: row for row in reader}


def parse_float(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return float("nan")


def format_delta(value: float) -> str:
    if value != value:
        return "n/a"
    return f"{value:+.1f}%"


def compare_metric(
    actual: float,
    baseline: float,
    threshold_pct: float,
    higher_is_worse: bool,
) -> tuple[str, bool]:
    if baseline == 0:
        return "n/a", False
    delta_pct = ((actual - baseline) / baseline) * 100
    if higher_is_worse:
        degraded = actual > baseline * (1 + threshold_pct / 100)
    else:
        degraded = actual < baseline * (1 - threshold_pct / 100)
    return format_delta(delta_pct), degraded


def main() -> None:
    args = parse_args()
    baseline_data = load_baselines(args.baseline)
    stats = load_stats(args.stats)

    default_threshold_pct = args.threshold_pct
    if default_threshold_pct is None:
        default_threshold_pct = float(baseline_data.get("threshold_pct", 20))

    thresholds_by_group: dict[str, float] = {
        key: float(value)
        for key, value in baseline_data.get("thresholds_pct", {}).items()
    }
    benchmark_groups: dict[str, str] = baseline_data.get("benchmark_groups", {})

    comparisons: list[str] = []
    failures: list[str] = []

    comparisons.append("## Benchmark Comparison")
    comparisons.append("")
    comparisons.append(
        f"Default threshold: {default_threshold_pct:.0f}% degradation allowed"
    )
    if thresholds_by_group:
        comparisons.append("Group thresholds:")
        for group_name in sorted(thresholds_by_group):
            comparisons.append(
                f"- `{group_name}`: {thresholds_by_group[group_name]:.0f}%"
            )
    comparisons.append("")
    comparisons.append(
        "| Name | Group | Metric | Baseline | Actual | Delta | Threshold | Status |"
    )
    comparisons.append("| --- | --- | --- | --- | --- | --- | --- | --- |")

    metrics: dict[str, dict[str, float]] = baseline_data.get("metrics", {})
    for name, baseline_metrics in metrics.items():
        row = stats.get(name)
        benchmark_group = benchmark_groups.get(name, "default")
        threshold_pct = thresholds_by_group.get(
            benchmark_group, default_threshold_pct
        )
        if not row:
            failures.append(f"{name} (missing)")
            comparisons.append(
                f"| {name} | {benchmark_group} | all | n/a | n/a | n/a | {threshold_pct:.0f}% | ❌ missing |"
            )
            continue

        for metric_key, baseline_value in baseline_metrics.items():
            if metric_key == "avg_ms":
                actual = parse_float(row["Average response time"])
                delta, degraded = compare_metric(
                    actual, baseline_value, threshold_pct, higher_is_worse=True
                )
                status = "❌" if degraded else "✅"
                if degraded:
                    failures.append(f"{name} avg_ms")
                comparisons.append(
                    f"| {name} | {benchmark_group} | avg_ms | {baseline_value:.1f} | {actual:.1f} | {delta} | {threshold_pct:.0f}% | {status} |"
                )
            elif metric_key == "p95_ms":
                actual = parse_float(row["95%"])
                delta, degraded = compare_metric(
                    actual, baseline_value, threshold_pct, higher_is_worse=True
                )
                status = "❌" if degraded else "✅"
                if degraded:
                    failures.append(f"{name} p95_ms")
                comparisons.append(
                    f"| {name} | {benchmark_group} | p95_ms | {baseline_value:.1f} | {actual:.1f} | {delta} | {threshold_pct:.0f}% | {status} |"
                )
            elif metric_key == "rps":
                actual = parse_float(row["Requests/s"])
                delta, degraded = compare_metric(
                    actual, baseline_value, threshold_pct, higher_is_worse=False
                )
                status = "❌" if degraded else "✅"
                if degraded:
                    failures.append(f"{name} rps")
                comparisons.append(
                    f"| {name} | {benchmark_group} | rps | {baseline_value:.2f} | {actual:.2f} | {delta} | {threshold_pct:.0f}% | {status} |"
                )

    comparisons.append("")
    if failures:
        comparisons.append(f"Overall status: ❌ Failed ({', '.join(failures)})")
    else:
        comparisons.append("Overall status: ✅ Passed")

    args.output.write_text("\n".join(comparisons) + "\n", encoding="utf-8")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

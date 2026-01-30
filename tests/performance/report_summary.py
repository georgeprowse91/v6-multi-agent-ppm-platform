from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a markdown summary from Locust CSV output.")
    parser.add_argument("--csv-prefix", required=True, help="CSV prefix used by Locust")
    parser.add_argument("--output", required=True, help="Markdown output path")
    return parser.parse_args()


def load_stats(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def format_row(row: dict[str, str]) -> str:
    return (
        f"| {row['Name']} | {row['# requests']} | {row['# failures']} | "
        f"{row['Requests/s']} | {row['Average response time']} | {row['95%']} |"
    )


def main() -> None:
    args = parse_args()
    stats_path = Path(f"{args.csv_prefix}_stats.csv")

    rows = load_stats(stats_path)
    if not rows:
        raise SystemExit("No Locust stats rows found")

    summary_lines = [
        "## Performance Test Summary",
        "",
        f"Source: `{stats_path}`",
        "",
        "| Name | Requests | Failures | RPS | Avg Latency (ms) | P95 Latency (ms) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for row in rows:
        summary_lines.append(format_row(row))

    output_path = Path(args.output)
    output_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

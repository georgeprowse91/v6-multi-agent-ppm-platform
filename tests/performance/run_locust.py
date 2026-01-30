from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import yaml

DEFAULT_CONFIG = Path(__file__).with_name("config.yaml")
DEFAULT_LOCUSTFILE = Path(__file__).with_name("locustfile.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Locust performance tests using config values.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to config YAML")
    parser.add_argument("--locustfile", type=Path, default=DEFAULT_LOCUSTFILE, help="Path to locustfile")
    parser.add_argument("--csv-prefix", type=str, default="tests/performance/results/perf")
    parser.add_argument("--log-level", type=str, default="INFO")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with args.config.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    users = config.get("users", 1)
    spawn_rate = config.get("spawn_rate", 1)
    run_time = config.get("run_time", "30s")
    host = config.get("host")

    csv_path = Path(args.csv_prefix)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "locust",
        "-f",
        str(args.locustfile),
        "--headless",
        "--users",
        str(users),
        "--spawn-rate",
        str(spawn_rate),
        "--run-time",
        str(run_time),
        "--csv",
        str(csv_path),
        "--loglevel",
        args.log_level,
    ]

    if host:
        command.extend(["--host", host])

    env = {"PERF_CONFIG": str(args.config), **dict(**os.environ)}

    subprocess.run(command, check=True, env=env)


if __name__ == "__main__":
    main()

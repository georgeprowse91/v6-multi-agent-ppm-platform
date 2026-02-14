#!/usr/bin/env python3
"""Lightweight local smoke check for workspace methodology wiring."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
METHODOLOGY_DOCS_DIR = REPO_ROOT / "docs" / "methodology"
FRONTEND_STORE_PATH = (
    REPO_ROOT / "apps" / "web" / "frontend" / "src" / "store" / "methodology" / "useMethodologyStore.ts"
)
METHODOLOGIES = ("predictive", "adaptive", "hybrid")


class SmokeFailure(RuntimeError):
    """Raised for smoke-check assertion failures."""


def _log(status: str, message: str) -> None:
    print(f"[{status}] {message}")


def _http_json(url: str, timeout_s: float = 5.0) -> dict[str, Any]:
    with urlopen(url, timeout=timeout_s) as response:  # nosec B310 - local smoke check
        return json.loads(response.read().decode("utf-8"))


def _is_backend_healthy(base_url: str) -> bool:
    try:
        _http_json(f"{base_url}/healthz", timeout_s=2.0)
        return True
    except Exception:
        return False


def _start_backend(base_url: str) -> subprocess.Popen[str]:
    host = "127.0.0.1"
    port = base_url.rsplit(":", 1)[-1]
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        host,
        "--port",
        port,
        "--app-dir",
        str(REPO_ROOT / "apps" / "web" / "src"),
    ]

    _log("INFO", f"Starting backend: {' '.join(cmd)}")
    process = subprocess.Popen(  # noqa: S603
        cmd,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
        text=True,
    )

    deadline = time.time() + 45
    while time.time() < deadline:
        if process.poll() is not None:
            stderr_output = ""
            if process.stderr is not None:
                stderr_output = process.stderr.read().strip()
            detail = f" Details: {stderr_output}" if stderr_output else ""
            raise SmokeFailure("Backend process exited before becoming healthy." + detail)
        if _is_backend_healthy(base_url):
            _log("PASS", "Backend started and /healthz is reachable.")
            return process
        time.sleep(1)

    process.terminate()
    raise SmokeFailure("Timed out waiting for backend /healthz.")


def _load_yaml_map(methodology_id: str) -> dict[str, Any]:
    path = METHODOLOGY_DOCS_DIR / methodology_id / "map.yaml"
    if not path.exists():
        raise SmokeFailure(f"Missing YAML map: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise SmokeFailure(f"Invalid YAML map payload: {path}")
    return payload


def _validate_workspace_payload(base_url: str, methodology_id: str) -> None:
    params = urlencode({"methodology": methodology_id})
    url = f"{base_url}/api/workspace/demo-1?{params}"
    payload = _http_json(url)

    available = payload.get("available_methodologies", [])
    expected = set(METHODOLOGIES)
    missing = expected.difference(set(available))
    if missing:
        raise SmokeFailure(
            f"{methodology_id}: missing methodologies in available_methodologies: {sorted(missing)}"
        )

    summary = payload.get("methodology_map_summary", {})
    stages = summary.get("stages", [])
    if not stages:
        raise SmokeFailure(f"{methodology_id}: methodology_map_summary.stages is empty")

    activity_total = sum(len(stage.get("activities", [])) for stage in stages if isinstance(stage, dict))
    if activity_total <= 0:
        raise SmokeFailure(f"{methodology_id}: stages contain zero activities")

    _log(
        "PASS",
        f"{methodology_id}: stages={len(stages)} activities={activity_total} methodologies={sorted(set(available))}",
    )


def _validate_gates(base_url: str, methodology_id: str) -> None:
    params = urlencode({"methodology_id": methodology_id})
    url = f"{base_url}/api/methodology/editor?{params}"
    payload = _http_json(url)
    gates = payload.get("gates", [])
    if methodology_id in {"predictive", "hybrid"} and not gates:
        raise SmokeFailure(f"{methodology_id}: expected non-empty gates list")
    _log("PASS", f"{methodology_id}: gates entries={len(gates)}")


def _validate_frontend_hydration_path() -> None:
    source = FRONTEND_STORE_PATH.read_text(encoding="utf-8")
    required_snippets = [
        "const payload = await fetchWorkspaceState(projectId, methodology);",
        "const mapped = mapWorkspaceResponseToProjectMethodology(payload);",
        "availableMethodologies: payload.available_methodologies",
        "Falling back to local demo methodology",
    ]
    missing = [snippet for snippet in required_snippets if snippet not in source]
    if missing:
        raise SmokeFailure(
            "Frontend hydration path check failed; missing expected store snippets: "
            + "; ".join(missing)
        )
    _log("PASS", "Frontend hydration path uses backend payload and has fallback behavior.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8501", help="Backend base URL")
    args = parser.parse_args()

    backend_process: subprocess.Popen[str] | None = None
    started_backend = False

    try:
        _log("INFO", "Validating YAML methodology maps load.")
        for methodology_id in METHODOLOGIES:
            _load_yaml_map(methodology_id)
            _log("PASS", f"{methodology_id}: map.yaml loaded")

        if _is_backend_healthy(args.base_url):
            _log("INFO", f"Using already-running backend at {args.base_url}")
        else:
            backend_process = _start_backend(args.base_url)
            started_backend = True

        _log("INFO", "Validating workspace endpoint responses.")
        for methodology_id in METHODOLOGIES:
            _validate_workspace_payload(args.base_url, methodology_id)

        _log("INFO", "Validating gates for predictive/hybrid.")
        _validate_gates(args.base_url, "predictive")
        _validate_gates(args.base_url, "hybrid")

        _log("INFO", "Validating frontend hydration path wiring.")
        _validate_frontend_hydration_path()

        _log("PASS", "Smoke check completed successfully.")
        return 0
    except (SmokeFailure, URLError, json.JSONDecodeError) as exc:
        _log("FAIL", str(exc))
        return 1
    finally:
        if started_backend and backend_process and backend_process.poll() is None:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()


if __name__ == "__main__":
    raise SystemExit(main())

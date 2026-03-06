"""Generic component runner for apps, services, agents, and connectors.

This CLI discovers components from the repo layout and provides a thin
run wrapper that selects the best execution strategy available.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tools import runtime_paths as _runtime_paths


def _path_fn(name: str):
    fn = getattr(_runtime_paths, name, None)
    if fn is not None:
        return fn

    root = Path(__file__).resolve().parents[2]
    fallbacks = {
        "repo_root": lambda: root,
        "apps_dir": lambda: root / "apps",
        "services_dir": lambda: root / "services",
        "agents_dir": lambda: root / "agents",
        "connectors_dir": lambda: root / "connectors",
        "integrations_services_dir": lambda: root / "integrations" / "services",
    }
    if name not in fallbacks:
        raise AttributeError(f"Unknown runtime path function: {name}")
    return fallbacks[name]


@dataclass(frozen=True)
class Component:
    """Metadata about a runnable component."""

    name: str
    component_type: str
    path: Path


def _iter_dirs(base: Path) -> Iterable[Path]:
    return (path for path in base.iterdir() if path.is_dir() and not path.name.startswith("."))


def discover_apps() -> list[Component]:
    """Discover application components under apps/."""

    app_roots = [_path_fn("apps_dir")()]
    return [
        Component(path.name, "app", path)
        for root in app_roots
        for path in _iter_dirs(root)
    ]


def discover_services() -> list[Component]:
    """Discover service components under services/."""

    service_roots = [_path_fn("services_dir")()]
    try:
        service_roots.append(_path_fn("integrations_services_dir")())
    except FileNotFoundError:
        pass
    return [
        Component(path.name, "service", path)
        for root in service_roots
        for path in _iter_dirs(root)
    ]


def discover_agents() -> list[Component]:
    """Discover agent components under agents/**/*-agent/."""

    agent_paths = sorted(_path_fn("agents_dir")().glob("**/*-agent"))
    return [Component(path.name, "agent", path) for path in agent_paths if path.is_dir()]


def discover_connectors() -> list[Component]:
    """Discover connector components with a manifest.yaml."""

    connectors = []
    for path in _iter_dirs(_path_fn("connectors_dir")()):
        manifest = path / "manifest.yaml"
        if manifest.exists():
            connectors.append(Component(path.name, "connector", path))
    return connectors


def list_components(component_type: str | None = None) -> list[Component]:
    """List components of a given type or all."""

    components: list[Component] = []
    if component_type in (None, "app"):
        components.extend(discover_apps())
    if component_type in (None, "service"):
        components.extend(discover_services())
    if component_type in (None, "agent"):
        components.extend(discover_agents())
    if component_type in (None, "connector"):
        components.extend(discover_connectors())
    return components


def _find_component(component_type: str, name: str) -> Component:
    for component in list_components(component_type):
        if component.name == name:
            return component
    available = ", ".join(sorted(c.name for c in list_components(component_type)))
    raise SystemExit(
        f"Unknown {component_type} '{name}'. Available: {available or 'none discovered'}."
    )


def _detect_streamlit(root: Path) -> list[str] | None:
    streamlit_app = root / "streamlit_app.py"
    if streamlit_app.exists():
        return ["streamlit", "run", str(streamlit_app)]
    return None


def _detect_uvicorn(root: Path) -> list[str] | None:
    src_dir = root / "src"
    candidate = src_dir / "api" / "main.py"
    if candidate.exists():
        return [
            "uvicorn",
            "api.main:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--app-dir",
            str(src_dir),
        ]
    main_app = src_dir / "main.py"
    if main_app.exists():
        return [
            "uvicorn",
            "main:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "8501",
            "--app-dir",
            str(src_dir),
        ]
    return None


def _detect_python_module(root: Path) -> list[str] | None:
    src_dir = root / "src"
    if not src_dir.exists():
        return None

    entrypoints = sorted(src_dir.glob("**/__main__.py"))
    if entrypoints:
        module = ".".join(entrypoints[0].relative_to(src_dir).with_suffix("").parts[:-1])
        if module:
            return ["python", "-m", module]

    main_files = sorted(src_dir.glob("**/main.py"))
    if main_files:
        module = ".".join(main_files[0].relative_to(src_dir).with_suffix("").parts)
        return ["python", "-m", module]

    return None


def _detect_node(root: Path) -> list[str] | None:
    package_json = root / "package.json"
    if not package_json.exists():
        return None
    try:
        content = json.loads(package_json.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid package.json at {package_json}: {exc}") from exc

    scripts = content.get("scripts", {})
    for script in ("dev", "start", "serve"):
        if script in scripts:
            return ["npm", "run", script]
    raise SystemExit(f"No runnable scripts found in {package_json}. Add a dev/start/serve script.")


def _detect_docker_ports(dockerfile: Path) -> list[str]:
    ports: list[str] = []
    for line in dockerfile.read_text().splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("EXPOSE"):
            ports.extend(part for part in stripped.split()[1:] if part.isdigit())
    return ports


def _run_docker(root: Path, name: str) -> None:
    dockerfile = root / "Dockerfile"
    if not dockerfile.exists():
        raise SystemExit(f"No Dockerfile found at {dockerfile}.")

    image_tag = f"ppm-{name}"
    subprocess.run(
        ["docker", "build", "-t", image_tag, "-f", str(dockerfile), str(root)],
        check=True,
    )

    ports = _detect_docker_ports(dockerfile)
    port_args = [arg for port in ports for arg in ("-p", f"{port}:{port}")]
    subprocess.run(["docker", "run", "--rm", *port_args, image_tag], check=True)


def _run_component(component: Component, use_docker: bool, dry_run: bool) -> None:
    root = component.path

    if component.component_type == "agent":
        command = ["python", "-m", "tools.agent_runner", "run-agent", "--name", component.name]
        if use_docker:
            command.append("--docker")
        _execute(command, _path_fn("repo_root")(), dry_run)
        return

    if component.component_type == "connector":
        command = [
            "python",
            "-m",
            "tools.connector_runner",
            "run-connector",
            "--name",
            component.name,
        ]
        if dry_run:
            command.append("--dry-run")
        _execute(command, _path_fn("repo_root")(), dry_run)
        return

    if use_docker:
        _run_docker(root, component.name)
        return

    run_command = (
        _detect_node(root)
        or _detect_streamlit(root)
        or _detect_uvicorn(root)
        or _detect_python_module(root)
    )
    if run_command is None:
        raise SystemExit(
            "No runnable entrypoint detected. Add one of the following to "
            f"{root}: package.json scripts, src/**/main.py, "
            "or src/**/__main__.py. If the component uses Docker, rerun with --docker."
        )

    _execute(run_command, root, dry_run)


def _execute(command: list[str], cwd: Path, dry_run: bool) -> None:
    display = " ".join(command)
    if dry_run:
        print(f"[dry-run] {display}")
        return
    subprocess.run(command, check=True, cwd=cwd)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Component discovery and runner.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available components.")
    list_parser.add_argument(
        "--type", choices=["app", "service", "agent", "connector"], help="Filter by type."
    )
    list_parser.add_argument("--json", action="store_true", help="Output JSON.")

    run_parser = subparsers.add_parser("run", help="Run a component.")
    run_parser.add_argument(
        "--type", required=True, choices=["app", "service", "agent", "connector"]
    )
    run_parser.add_argument("--name", required=True)
    run_parser.add_argument("--docker", action="store_true", help="Run using Dockerfile.")
    run_parser.add_argument("--dry-run", action="store_true", help="Print the run command.")

    return parser.parse_args()


def _render_components(components: list[Component], as_json: bool) -> None:
    if as_json:
        payload = [
            {"name": c.name, "type": c.component_type, "path": str(c.path)} for c in components
        ]
        print(json.dumps(payload, indent=2))
        return

    for component in components:
        print(f"{component.component_type}: {component.name} -> {component.path}")


def main() -> None:
    args = _parse_args()
    if args.command == "list":
        components = list_components(args.type)
        _render_components(components, args.json)
        return

    component = _find_component(args.type, args.name)
    _run_component(component, args.docker, args.dry_run)


if __name__ == "__main__":
    main()

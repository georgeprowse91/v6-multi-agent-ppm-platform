"""Agent runner CLI for listing and running agent components."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from tools.component_runner import Component, discover_agents
from tools.runtime_paths import repo_root


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent runner for local development.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-agents", help="List available agents.")
    list_parser.add_argument("--json", action="store_true", help="Output JSON.")

    run_parser = subparsers.add_parser("run-agent", help="Run a single agent.")
    run_parser.add_argument("--id", help="Agent id suffix (e.g., 10).")
    run_parser.add_argument("--name", help="Full agent folder name.")
    run_parser.add_argument("--docker", action="store_true", help="Run using Dockerfile.")
    run_parser.add_argument("--dry-run", action="store_true", help="Print command without running.")

    return parser.parse_args()


def _format_agent_id(agent: Component) -> str:
    parts = agent.name.split("-", maxsplit=2)
    if len(parts) >= 2 and parts[1].isdigit():
        return parts[1]
    return agent.name


def _select_agent(agent_id: str | None, name: str | None) -> Component:
    agents = discover_agents()
    if name:
        for agent in agents:
            if agent.name == name:
                return agent
        raise SystemExit(f"Agent '{name}' not found.")

    if agent_id:
        for agent in agents:
            if _format_agent_id(agent) == agent_id:
                return agent
        raise SystemExit(f"Agent with id '{agent_id}' not found.")

    raise SystemExit("Provide --id or --name to run an agent.")


def _run_agent(agent: Component, use_docker: bool, dry_run: bool) -> None:
    if use_docker:
        dockerfile = agent.path / "Dockerfile"
        if not dockerfile.exists():
            raise SystemExit(f"No Dockerfile found for {agent.name} at {dockerfile}.")
        image_tag = f"ppm-agent-{agent.name}"
        commands = [
            ["docker", "build", "-t", image_tag, "-f", str(dockerfile), str(agent.path)],
            ["docker", "run", "--rm", image_tag],
        ]
        for command in commands:
            _execute(command, repo_root(), dry_run)
        return

    runner = Path("tools/agent_runner_core.py")
    if not runner.exists():
        raise SystemExit("Missing tools/agent_runner_core.py. Add a runtime entrypoint.")
    command = [
        "python",
        "-m",
        "tools.agent_runner_core",
        "--agent-path",
        str(_default_agent_entrypoint(agent)),
    ]
    _execute(command, repo_root(), dry_run)


def _default_agent_entrypoint(agent: Component) -> Path:
    candidates = sorted(agent.path.glob("**/src/**/*.py"))
    for candidate in candidates:
        if candidate.name != "__init__.py":
            return candidate
    raise SystemExit(f"No Python entrypoint found under {agent.path}. Add a module under src/.")


def _execute(command: list[str], cwd: Path, dry_run: bool) -> None:
    display = " ".join(command)
    if dry_run:
        print(f"[dry-run] {display}")
        return
    subprocess.run(command, check=True, cwd=cwd)


def _render_agents(agents: list[Component], as_json: bool) -> None:
    if as_json:
        import json

        payload = [{"name": agent.name, "path": str(agent.path)} for agent in agents]
        print(json.dumps(payload, indent=2))
        return

    for agent in agents:
        print(f"{agent.name} -> {agent.path}")


def main() -> None:
    args = _parse_args()

    if args.command == "list-agents":
        _render_agents(discover_agents(), args.json)
        return

    agent = _select_agent(args.id, args.name)
    _run_agent(agent, args.docker, args.dry_run)


if __name__ == "__main__":
    main()

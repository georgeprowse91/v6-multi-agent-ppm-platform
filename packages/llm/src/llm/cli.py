from __future__ import annotations

import argparse
from pathlib import Path

from llm.prompts import PromptRegistry


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prompt registry CLI")
    parser.add_argument("--registry", type=Path, default=None, help="Registry JSON path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Register a new prompt")
    register.add_argument("name")
    register.add_argument("content")

    promote = subparsers.add_parser("promote", help="Promote a prompt version")
    promote.add_argument("name")
    promote.add_argument("version", type=int)
    promote.add_argument("status", choices=["staging", "production", "retired"])

    subparsers.add_parser("list", help="List prompt versions")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    registry = PromptRegistry(args.registry)

    if args.command == "register":
        record = registry.register_prompt(args.name, args.content)
        print(f"Registered {record.name} v{record.version} ({record.status})")
    elif args.command == "promote":
        record = registry.promote_prompt(args.name, args.version, args.status)
        print(f"Promoted {record.name} v{record.version} to {record.status}")
    elif args.command == "list":
        for record in registry.list_prompts():
            print(f"{record.name} v{record.version} [{record.status}] - {record.updated_at}")


if __name__ == "__main__":
    main()

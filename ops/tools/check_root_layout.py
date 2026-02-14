from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ROOT_ENTRIES = {
    ".devcontainer",
    ".dockerignore",
    ".env.demo",
    ".env.example",
    ".git",
    ".gitattributes",
    ".github",
    ".gitignore",
    ".pre-commit-config.yaml",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "Makefile",
    "README.md",
    "SECURITY.md",
    "agents",
    "alembic.ini",
    "apps",
    "config",
    "data",
    "design-system",
    "docker-compose.test.yml",
    "docker-compose.yml",
    "docs",
    "examples",
    "infra",
    "integrations",
    "jinja2",
    "jsonschema",
    "mkdocs.yml",
    "node_modules",
    "ops",
    "packages",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "policies",
    "prompt_registry.py",
    "prompts",
    "pydantic_settings.py",
    "pyproject.toml",
    "requirements-dev.in",
    "requirements-dev.txt",
    "requirements.in",
    "requirements.txt",
    "runtime_flags.py",
    "scripts",
    "services",
    "tests",
}


def find_unexpected_root_entries(repo_root: Path) -> list[str]:
    root_entries = {entry.name for entry in repo_root.iterdir()}
    unexpected = sorted(root_entries - ALLOWED_ROOT_ENTRIES)
    return unexpected


def main() -> int:
    unexpected = find_unexpected_root_entries(REPO_ROOT)
    if unexpected:
        print("Unexpected repository root entries detected:")
        for name in unexpected:
            print(f" - {name}")
        print("\nIf intentional, update docs/root-file-policy.md and ops/tools/check_root_layout.py.")
        return 1

    print("Repository root layout check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ROOT_ENTRIES = {
    ".claude",
    ".devcontainer",
    ".dockerignore",
    ".git",
    ".gitattributes",
    ".github",
    ".gitignore",
    ".gitleaks.toml",
    ".pre-commit-config.yaml",
    "CLAUDE.md",
    "CODEBASE_ISSUES.md",
    "CONTRIBUTING.md",
    "INDEX.md",
    "LICENSE",
    "Makefile",
    "README.md",
    "SECURITY.md",
    "agents",
    "apps",
    "artifacts",
    "config",
    "connectors",
    "constraints",
    "data",
    "docs",
    "examples",
    "integrations",
    "mkdocs.yml",
    "node_modules",
    "ops",
    "packages",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "pyproject.toml",
    "requirements.txt",
    "security",
    "services",
    "tests",
    "tools",
    "vendor",
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

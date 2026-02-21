from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _join(*parts: str) -> str:
    return "".join(parts)


FILLER_PATTERNS = [
    _join("add", r"\s+", "here"),
    _join("what", r"\s+", "to", r"\s+", "add", r"\s+", "here"),
    _join("what", r"\s+", "belongs", r"\s+", "here"),
    _join("to", r"\s+", "be", r"\s+", "added"),
    _join("coming", r"\s+", "soon"),
    _join("t", "b", "d"),
    _join("to", "do"),
    _join("place", "holder"),
    _join("lorem", r"\s+", "ipsum"),
    _join("<", "insert"),
    _join("<", "to", "do"),
    _join("fill", r"\s+", "this"),
    _join("fix", "me"),
]

ALLOWED_TASK_MARKER = re.compile(
    r"\b(?:" + _join("TO", "DO") + r"|" + _join("FI", "XME") + r")\(#\d+\):"
)
ALLOWED_CONTEXT_PATTERNS = [
    re.compile(r"\bcheck-placeholders(?:\.py)?\b", re.IGNORECASE),
    re.compile(r'placeholder\s*[=:]\s*["\']', re.IGNORECASE),
    re.compile(r"def\s+\w*placeholder\w*|return\s+\w*placeholder\w*\(|\w*placeholder\w*,", re.IGNORECASE),
    re.compile(r"coming_soon|COMING_SOON", re.IGNORECASE),
    re.compile(r'["\'](?:todo|in_progress)["\']|status.*(?:todo|in_progress)', re.IGNORECASE),
    re.compile(r"\.placeholder|Placeholder\b(?!.*response)", re.IGNORECASE),
    re.compile(r"test_.*placeholder|placeholder.*test", re.IGNORECASE),
    re.compile(r"(?:Template|env)\s+placeholders?|placeholders?\s+(?:context|tokens|rendering|instead)", re.IGNORECASE),
    re.compile(r"(?:following|the|these)\s+placeholders?|substitution.*placeholders?", re.IGNORECASE),
    re.compile(r"integrity.*sha\d+", re.IGNORECASE),
]

IGNORED_FILES = {
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
}

TEXT_EXTENSIONS = {
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".graphql",
    ".gql",
}

IGNORED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}

PURPOSE_HEADER = re.compile(r"^##+\s+purpose\b", re.IGNORECASE)
RUN_HEADER = re.compile(r"^##+\s+(?:how\s+to\s+run|run(?:ning)?(?:\s+locally)?|local\s+development|develop(?:ment)?|quick\s*start)\b", re.IGNORECASE)
CONFIG_HEADER = re.compile(r"^##+\s+(?:configuration|config(?:uration)?|environment(?:\s+variables?)?)\b", re.IGNORECASE)
OWNERSHIP_HEADER = re.compile(r"^##+\s+(?:ownership|owner(?:ship)?|support|maintainers?)\b", re.IGNORECASE)
OWNERSHIP_METADATA = re.compile(
    r"\b(?:owner|maintainer|support|on[-\s]?call|slack|email|team)\b\s*[:|]",
    re.IGNORECASE,
)
MARKDOWN_HEADER = re.compile(r"^##+\s+")


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


CORE_DOCS = [
    Path("README.md"),
    Path("docs/README.md"),
    Path("docs/solution-index.md"),
]


def iter_placeholder_targets(root: Path) -> list[Path]:
    targets: list[Path] = []
    targets.extend(iter_component_readmes(root))

    for path in CORE_DOCS:
        candidate = root / path
        if candidate.exists():
            targets.append(candidate)

    return sorted({target.resolve() for target in targets})


def scan_file(
    path: Path, pattern: re.Pattern[str], allowlist: list[re.Pattern[str]] | None = None
) -> list[tuple[int, str]]:
    matches = []
    lines = path.read_text(errors="ignore").splitlines()
    for idx, line in enumerate(lines, start=1):
        if pattern.search(line):
            if path.name.endswith(".schema.json") and '"enum"' in line:
                continue
            if allowlist and any(allowed.search(line) for allowed in allowlist):
                continue
            matches.append((idx, line.strip()))
    return matches


def iter_component_readmes(root: Path) -> list[Path]:
    files: list[Path] = []
    for section in ("apps", "services"):
        section_path = root / section
        if not section_path.exists():
            continue
        for component_dir in section_path.iterdir():
            if not component_dir.is_dir():
                continue
            readme = component_dir / "README.md"
            if readme.exists():
                files.append(readme)
    return sorted(files)


def _extract_purpose_content(lines: list[str]) -> tuple[int | None, list[str]]:
    start_index: int | None = None
    for idx, line in enumerate(lines):
        if PURPOSE_HEADER.match(line.strip()):
            start_index = idx
            break
    if start_index is None:
        return None, []

    content: list[str] = []
    for line in lines[start_index + 1 :]:
        if MARKDOWN_HEADER.match(line.strip()):
            break
        if line.strip():
            content.append(line.strip())
    return start_index + 1, content


def _has_section(lines: list[str], pattern: re.Pattern[str]) -> bool:
    return any(pattern.match(line.strip()) for line in lines)


def check_component_completeness(root: Path) -> list[str]:
    violations: list[str] = []
    filler_regex = re.compile("|".join(FILLER_PATTERNS), re.IGNORECASE)

    for readme in iter_component_readmes(root):
        lines = readme.read_text(errors="ignore").splitlines()
        rel = readme.relative_to(root)

        purpose_line, purpose_content = _extract_purpose_content(lines)
        if purpose_line is None:
            violations.append(f"{rel}: missing required section: Purpose (add '## Purpose' with a concrete description)")
        elif not purpose_content:
            violations.append(f"{rel}:{purpose_line}: purpose section is empty (document what this component does)")
        else:
            joined = " ".join(purpose_content)
            if filler_regex.search(joined):
                violations.append(f"{rel}:{purpose_line}: purpose section contains placeholder text (replace with concrete component purpose)")

        if not _has_section(lines, RUN_HEADER):
            violations.append(f"{rel}: missing run instructions section (add '## Running locally' or equivalent with executable commands)")

        if not _has_section(lines, CONFIG_HEADER):
            violations.append(f"{rel}: missing configuration section (add '## Configuration' or environment variables documentation)")

        has_ownership_header = _has_section(lines, OWNERSHIP_HEADER)
        has_ownership_metadata = any(OWNERSHIP_METADATA.search(line) for line in lines)
        if not (has_ownership_header or has_ownership_metadata):
            violations.append(
                f"{rel}: missing ownership/support metadata (add owner/team/support contact details)")

    return violations


def run_checks(root: Path) -> list[str]:
    violations: list[str] = []
    filler_regex = re.compile("|".join(FILLER_PATTERNS), re.IGNORECASE)
    describe_stub_regex = re.compile(r"^\s*(?:[-*]\s+)?describe\b", re.IGNORECASE)
    task_marker_regex = re.compile(
        r"\b(?:" + _join("TO", "DO") + r"|" + _join("FI", "XME") + r")\b"
    )

    for path in iter_placeholder_targets(root):
        filler_hits = scan_file(path, filler_regex, ALLOWED_CONTEXT_PATTERNS)
        for line_no, line in filler_hits:
            violations.append(f"{path.relative_to(root)}:{line_no}: forbidden phrase found: {line}")

        describe_stub_hits = scan_file(path, describe_stub_regex)
        for line_no, line in describe_stub_hits:
            violations.append(f"{path.relative_to(root)}:{line_no}: forbidden scaffold phrase found: {line}")

        task_marker_hits = scan_file(path, task_marker_regex)
        for line_no, line in task_marker_hits:
            if ALLOWED_TASK_MARKER.search(line):
                continue
            violations.append(
                f"{path.relative_to(root)}:{line_no}: task markers must include issue reference: {line}"
            )

    violations.extend(check_component_completeness(root))
    return violations


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check repository for placeholders and incomplete component READMEs.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root to scan.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    violations = run_checks(root)

    if violations:
        print("Repository quality gate failed:")
        for violation in violations:
            print(f"  - {violation}")
        print("\nAction: resolve each item above before merging or releasing.")
        return 1

    print("Repository quality gate passed: no placeholders or component README completeness issues detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

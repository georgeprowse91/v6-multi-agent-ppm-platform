#!/usr/bin/env python3
"""Generate agent catalog markdown and UI JSON from agent README files."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[2]
AGENT_README_GLOB = "agents/**/agent-*/README.md"
CATALOG_PATH = ROOT_DIR / "agents" / "AGENT_CATALOG.md"
AGENTS_JSON_PATH = ROOT_DIR / "apps" / "web" / "data" / "agents.json"


@dataclass(frozen=True)
class Section:
    heading: str
    content: list[str]


@dataclass(frozen=True)
class AgentMetadata:
    agent_id: int
    title: str
    component_name: str
    source_file: str
    domain: str
    sections: list[Section]


def iter_agent_readmes(root_dir: Path) -> Iterable[Path]:
    return sorted({path.resolve() for path in root_dir.glob(AGENT_README_GLOB)})


def parse_sections(lines: list[str]) -> list[Section]:
    sections: list[Section] = []
    current_heading: str | None = None
    buffer: list[str] = []
    in_code_block = False

    def flush() -> None:
        nonlocal buffer, current_heading
        if current_heading is None:
            buffer = []
            return
        content = [item for item in buffer if item]
        sections.append(Section(heading=current_heading, content=content))
        buffer = []

    paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            buffer.append(" ".join(paragraph).strip())
            paragraph = []

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if line.startswith("## "):
            flush_paragraph()
            flush()
            current_heading = line[3:].strip()
            continue
        if not line.strip():
            flush_paragraph()
            continue
        if line.lstrip().startswith("- "):
            flush_paragraph()
            buffer.append(line.lstrip()[2:].strip())
            continue
        if re.match(r"^\d+\.\s+", line.strip()):
            flush_paragraph()
            buffer.append(re.sub(r"^\d+\.\s+", "", line.strip()))
            continue
        paragraph.append(line.strip())

    flush_paragraph()
    flush()
    return sections


def parse_agent_readme(path: Path) -> AgentMetadata:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    title = "Untitled Agent"
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    component_name = path.parent.name
    match = re.match(r"agent-(\d+)-", component_name)
    if not match:
        raise ValueError(f"Could not determine agent ID from {component_name}")
    agent_id = int(match.group(1))
    domain = path.parent.parent.name
    sections = parse_sections(lines)
    canonical_title = f"Agent {agent_id:02d}: {title.split(':', 1)[1].strip()}" if ":" in title else title
    return AgentMetadata(
        agent_id=agent_id,
        title=canonical_title,
        component_name=component_name,
        source_file=str(path.relative_to(ROOT_DIR)),
        domain=domain,
        sections=sections,
    )


def build_agents_json(agents: list[AgentMetadata]) -> dict:
    return {
        "source_dir": AGENT_README_GLOB,
        "agents": [
            {
                "id": agent.agent_id,
                "title": agent.title,
                "sections": [
                    {"heading": section.heading, "content": section.content}
                    for section in agent.sections
                ],
                "source_file": agent.source_file,
            }
            for agent in agents
        ],
    }


def title_case_domain(domain: str) -> str:
    return domain.replace("-", " ").title()


def build_agent_catalog(agents: list[AgentMetadata]) -> str:
    grouped: dict[str, list[AgentMetadata]] = {}
    for agent in agents:
        grouped.setdefault(agent.domain, []).append(agent)

    lines = [
        "# Agent Catalogue",
        "",
        "This catalogue is generated from the agent README files under",
        f"`{AGENT_README_GLOB}`. Update the README content and rerun the",
        "generator to refresh this file and the web UI metadata.",
        "",
    ]

    for domain in sorted(grouped.keys()):
        lines.append(f"## {title_case_domain(domain)}")
        lines.append("")
        for agent in sorted(grouped[domain], key=lambda item: item.agent_id):
            lines.append(f"### {agent.title} (`{agent.component_name}`)")
            lines.append(f"- **Location:** `{agent.source_file.rsplit('/', 1)[0]}`")
            purpose = next(
                (section for section in agent.sections if section.heading == "Purpose"),
                None,
            )
            if purpose and purpose.content:
                lines.append("- **Purpose:**")
                for entry in purpose.content:
                    lines.append(f"  - {entry}")
            else:
                lines.append("- **Purpose:** Not documented in README.")
            lines.append("")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_if_changed(path: Path, content: str) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def check_consistency(path: Path, content: str) -> list[str]:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current == content:
        return []
    diff = difflib.unified_diff(
        current.splitlines(),
        content.splitlines(),
        fromfile=str(path),
        tofile=f"{path} (generated)",
        lineterm="",
    )
    return list(diff)


def generate_outputs(root_dir: Path) -> tuple[str, str]:
    agents = [parse_agent_readme(path) for path in iter_agent_readmes(root_dir)]
    agents.sort(key=lambda item: (item.agent_id, item.component_name))
    catalog = build_agent_catalog(agents)
    json_data = build_agents_json(agents)
    agents_json = json.dumps(json_data, indent=2, ensure_ascii=False) + "\n"
    return catalog, agents_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate agent catalog markdown and UI JSON from README files."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if generated output does not match committed files.",
    )
    args = parser.parse_args()

    catalog, agents_json = generate_outputs(ROOT_DIR)

    if args.check:
        catalog_diff = check_consistency(CATALOG_PATH, catalog)
        json_diff = check_consistency(AGENTS_JSON_PATH, agents_json)
        if catalog_diff or json_diff:
            if catalog_diff:
                print("\n".join(catalog_diff))
            if json_diff:
                print("\n".join(json_diff))
            return 1
        return 0

    write_if_changed(CATALOG_PATH, catalog)
    write_if_changed(AGENTS_JSON_PATH, agents_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

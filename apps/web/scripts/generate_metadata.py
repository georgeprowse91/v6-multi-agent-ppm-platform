#!/usr/bin/env python
"""Generate prototype metadata JSON from the repo's source docs (Markdown preferred).

Outputs:
- apps/web/data/requirements.json
- apps/web/data/agents.json

This is useful if you update the docs and want the prototype UI to reflect the latest text.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    # apps/web/scripts/generate_metadata.py -> repo root
    return Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data"


def parse_prd(prd_path: Path) -> dict[str, Any]:
    content = prd_path.read_text(encoding="utf-8")
    functional_sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in content.splitlines():
        txt = line.strip()
        if not txt:
            continue
        if txt.startswith("## "):
            if current:
                functional_sections.append(current)
            current = {"title": txt.lstrip("# ").strip(), "requirements": []}
        elif current and txt.startswith("- "):
            current["requirements"].append(txt.lstrip("- ").strip())

    if current:
        functional_sections.append(current)

    return {
        "source": str(prd_path.relative_to(repo_root())),
        "functional_domains": functional_sections,
        "non_functional_requirements": [],
    }


def parse_agent_doc(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    title = None
    sections = []
    current = None
    buf: list[str] = []
    for raw_line in content.splitlines():
        txt = raw_line.strip()
        if not txt:
            continue
        if txt.startswith("# "):
            title = txt.lstrip("# ").strip()
        elif txt.startswith("## "):
            if current:
                sections.append({"heading": current, "content": buf})
            current = txt.lstrip("# ").strip()
            buf = []
        else:
            if current:
                buf.append(txt)
    if current:
        sections.append({"heading": current, "content": buf})
    m = re.search(r"Agent\s+(\d+)", title or path.name)
    agent_id = int(m.group(1)) if m else 0
    return {
        "id": agent_id,
        "title": title or path.stem,
        "sections": sections,
        "source_file": str(path.relative_to(repo_root())),
    }


def main() -> int:
    root = repo_root()
    out_dir = data_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # PRD
    prd_candidates = list(root.glob("docs/product/product-requirements.md"))
    if not prd_candidates:
        raise FileNotFoundError("Could not find the Product Requirements markdown under docs/.")
    prd_path = prd_candidates[0]
    requirements = parse_prd(prd_path)
    (out_dir / "requirements.json").write_text(
        json.dumps(requirements, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Agents
    agent_docs = sorted(root.glob("agents/**/README.md"))
    agents = [parse_agent_doc(p) for p in agent_docs]
    agents_payload = {
        "source_dir": "agents/**/README.md",
        "agents": sorted(agents, key=lambda a: a.get("id", 0)),
    }
    (out_dir / "agents.json").write_text(
        json.dumps(agents_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Wrote {out_dir / 'requirements.json'}")
    print(f"Wrote {out_dir / 'agents.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx import Document


@dataclass
class DocRef:
    path: str
    title: str
    group: str


def repo_root() -> Path:
    # apps/web/ppm/docs.py -> repo root
    return Path(__file__).resolve().parents[4]


def list_docx() -> list[DocRef]:
    root = repo_root()
    candidates: list[tuple[str, str]] = [
        ("docs", "docs"),
        ("connectors", "connectors"),
    ]
    out: list[DocRef] = []
    for folder, group in candidates:
        base = root / folder
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.docx")):
            out.append(DocRef(path=str(p), title=p.stem, group=group))
    return out


def extract_docx_text(path: str, *, max_paragraphs: int | None = None) -> str:
    doc = Document(path)
    lines = []
    for i, para in enumerate(doc.paragraphs):
        t = (para.text or "").strip()
        if t:
            lines.append(t)
        if max_paragraphs is not None and i >= max_paragraphs:
            break
    return "\n".join(lines)


def search_docx(query: str, *, max_results: int = 25) -> list[dict[str, str]]:
    q = (query or "").strip().lower()
    if not q:
        return []
    results = []
    for d in list_docx():
        try:
            text = extract_docx_text(d.path, max_paragraphs=800).lower()
        except Exception:
            continue
        if q in text:
            results.append({"title": d.title, "path": d.path, "group": d.group})
        if len(results) >= max_results:
            break
    return results

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


class StrictUndefined:
    pass


@dataclass
class _ParsedTemplate:
    source: str


class _Template:
    def __init__(self, source: str) -> None:
        self.source = source

    def render(self, **kwargs: Any) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            if key not in kwargs:
                raise ValueError(f"'{key}' is undefined")
            return str(kwargs[key])

        return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", replace, self.source)


class Environment:
    def __init__(self, undefined: Any = None, autoescape: bool = False) -> None:
        self.undefined = undefined
        self.autoescape = autoescape

    def parse(self, source: str) -> _ParsedTemplate:
        return _ParsedTemplate(source=source)

    def from_string(self, source: str) -> _Template:
        return _Template(source)


class _MetaModule:
    @staticmethod
    def find_undeclared_variables(parsed: _ParsedTemplate) -> set[str]:
        return {m.group(1).strip() for m in re.finditer(r"\{\{\s*([^}]+?)\s*\}\}", parsed.source)}


meta = _MetaModule()

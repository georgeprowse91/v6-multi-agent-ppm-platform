import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import ast

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
MAX_MAIN_LINES = 120


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(SRC_ROOT).with_suffix("").parts)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_main_module_stays_small() -> None:
    main_path = SRC_ROOT / "main.py"
    assert len(main_path.read_text(encoding="utf-8").splitlines()) <= MAX_MAIN_LINES


def test_no_import_cycles_between_routes_services_dependencies() -> None:
    targets = [
        *SRC_ROOT.glob("routes/*.py"),
        *SRC_ROOT.glob("services/*.py"),
        SRC_ROOT / "dependencies.py",
    ]
    modules = {_module_name(path): path for path in targets if path.name != "__init__.py"}
    graph: dict[str, set[str]] = {name: set() for name in modules}

    for module_name, path in modules.items():
        for imported in _imports(path):
            for candidate in modules:
                if imported == candidate or imported.startswith(f"{candidate}."):
                    graph[module_name].add(candidate)

    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise AssertionError(f"Import cycle detected at {node}")
        visiting.add(node)
        for neighbour in graph[node]:
            _visit(neighbour)
        visiting.remove(node)
        visited.add(node)

    for module_name in modules:
        _visit(module_name)

#!/usr/bin/env python3
"""Generate code-derived API and connector documentation artifacts."""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from connectors.sdk.connector_maturity_inventory import build_inventory
SERVICES_ROOT = REPO_ROOT / "services"
CONNECTORS_ROOT = REPO_ROOT / "connectors"
GENERATED_SERVICES_ROOT = REPO_ROOT / "docs" / "generated" / "services"
GENERATED_CONNECTORS_ROOT = REPO_ROOT / "docs" / "connectors" / "generated"

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    handler: str


def _literal_str(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _parse_router_prefixes(tree: ast.Module) -> dict[str, str]:
    prefixes: dict[str, str] = {"app": ""}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        call_name = _call_name(node.value)
        if call_name not in {"APIRouter", "FastAPI"}:
            continue
        prefix = ""
        for keyword in node.value.keywords:
            if keyword.arg == "prefix":
                prefix = _literal_str(keyword.value) or ""
                break
        for target in node.targets:
            if isinstance(target, ast.Name):
                prefixes[target.id] = prefix
    return prefixes


def _path_from_decorator(call: ast.Call) -> str | None:
    if call.args:
        path = _literal_str(call.args[0])
        if path:
            return path
    for keyword in call.keywords:
        if keyword.arg in {"path", "url"}:
            return _literal_str(keyword.value)
    return None


def _methods_from_decorator(call: ast.Call, attr: str) -> list[str]:
    if attr in HTTP_METHODS:
        return [attr.upper()]
    for keyword in call.keywords:
        if keyword.arg == "methods" and isinstance(keyword.value, (ast.List, ast.Tuple, ast.Set)):
            methods = []
            for item in keyword.value.elts:
                method = _literal_str(item)
                if method:
                    methods.append(method.upper())
            if methods:
                return methods
    return []


def _join_paths(prefix: str, path: str) -> str:
    if not prefix:
        return path
    return f"{prefix.rstrip('/')}/{path.lstrip('/')}"


def _scan_service_routes(service_main: Path) -> tuple[str | None, list[Endpoint]]:
    tree = ast.parse(service_main.read_text(), filename=str(service_main))
    router_prefixes = _parse_router_prefixes(tree)

    title: str | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if _call_name(node.value) != "FastAPI":
            continue
        for keyword in node.value.keywords:
            if keyword.arg == "title":
                title = _literal_str(keyword.value)
                break

    endpoints: list[Endpoint] = []
    function_nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for function_node in function_nodes:
        for decorator in function_node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            owner = decorator.func.value
            attr = decorator.func.attr.lower()
            if not isinstance(owner, ast.Name):
                continue
            if attr not in HTTP_METHODS and attr != "api_route":
                continue
            path = _path_from_decorator(decorator)
            if not path:
                continue
            methods = _methods_from_decorator(decorator, attr)
            if not methods:
                continue
            prefix = router_prefixes.get(owner.id, "")
            full_path = _join_paths(prefix, path)
            for method in methods:
                endpoints.append(Endpoint(method=method, path=full_path, handler=function_node.name))

    endpoints.sort(key=lambda item: (item.path, item.method, item.handler))
    return title, endpoints


def _service_slug(service_dir: Path) -> str:
    return service_dir.name


def generate_service_docs() -> None:
    GENERATED_SERVICES_ROOT.mkdir(parents=True, exist_ok=True)
    index_lines = [
        "# Generated Service Endpoint Docs",
        "",
        "These files are generated from FastAPI route decorators in `services/*/src/main.py`.",
        "Do not edit by hand; run `python ops/tools/codegen/generate_docs.py`.",
        "",
        "| Service | Endpoint docs |",
        "| --- | --- |",
    ]

    for service_main in sorted(SERVICES_ROOT.glob("*/src/main.py")):
        service_dir = service_main.parent.parent
        slug = _service_slug(service_dir)
        title, endpoints = _scan_service_routes(service_main)
        output_path = GENERATED_SERVICES_ROOT / f"{slug}.md"

        lines = [
            f"# {title or slug} endpoint reference",
            "",
            f"Source: `{service_main.relative_to(REPO_ROOT)}`",
            "",
            "| Method | Path | Handler |",
            "| --- | --- | --- |",
        ]
        for endpoint in endpoints:
            lines.append(f"| `{endpoint.method}` | `{endpoint.path}` | `{endpoint.handler}` |")
        if not endpoints:
            lines.append("| _none_ | _none_ | _none_ |")

        output_path.write_text("\n".join(lines) + "\n")
        index_lines.append(f"| `{slug}` | [docs/generated/services/{slug}.md](./{slug}.md) |")

    (GENERATED_SERVICES_ROOT / "README.md").write_text("\n".join(index_lines) + "\n")


def _load_manifest(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) or {}


def generate_connector_docs() -> None:
    GENERATED_CONNECTORS_ROOT.mkdir(parents=True, exist_ok=True)
    inventory = build_inventory()
    (GENERATED_CONNECTORS_ROOT / "maturity-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")

    manifest_index: dict[str, dict[str, Any]] = {}
    for manifest_path in sorted(CONNECTORS_ROOT.glob("*/manifest.yaml")):
        manifest = _load_manifest(manifest_path)
        connector_id = manifest.get("id")
        if connector_id:
            manifest_index[str(connector_id)] = manifest

    lines = [
        "# Generated Connector Capability Matrix",
        "",
        "This table is generated from connector manifests plus the maturity inventory output.",
        "Do not edit by hand; run `python ops/tools/codegen/generate_docs.py`.",
        "",
        "| Connector | Name | Maturity level | Auth | Sync modes | Read | Write | Webhook | Mapping completeness |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for connector in inventory.get("connectors", []):
        connector_id = str(connector.get("id", ""))
        manifest = manifest_index.get(connector_id, {})
        auth_type = str(manifest.get("auth", {}).get("type", "unknown"))
        modes = manifest.get("sync", {}).get("modes", [])
        mode_str = ", ".join(str(mode) for mode in modes) if isinstance(modes, list) and modes else "n/a"
        coverage = connector.get("coverage", {})
        lines.append(
            "| `{id}` | {name} | {level} | `{auth}` | {modes} | {read} | {write} | {webhook} | {mapping:.2f} |".format(
                id=connector_id,
                name=str(connector.get("name", "")),
                level=connector.get("level", "-"),
                auth=auth_type,
                modes=mode_str,
                read="✅" if coverage.get("read") else "❌",
                write="✅" if coverage.get("write") else "❌",
                webhook="✅" if coverage.get("webhook") else "❌",
                mapping=float(coverage.get("mapping_completeness", 0.0)),
            )
        )

    lines.extend(
        [
            "",
            "## Inventory summary",
            "",
            f"- Total connectors: **{inventory['summary']['total_connectors']}**",
            f"- Read enabled: **{inventory['summary']['read_enabled']}**",
            f"- Write enabled: **{inventory['summary']['write_enabled']}**",
            f"- Webhook enabled: **{inventory['summary']['webhook_enabled']}**",
        ]
    )

    (GENERATED_CONNECTORS_ROOT / "capability-matrix.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    generate_service_docs()
    generate_connector_docs()
    print("Generated service endpoint and connector capability docs.")


if __name__ == "__main__":
    main()

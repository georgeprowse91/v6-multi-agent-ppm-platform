from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
CONNECTORS_ROOT = REPO_ROOT / "integrations" / "connectors"
SDK_PATH = CONNECTORS_ROOT / "sdk" / "src"


def bootstrap_connector_imports() -> None:
    """Install import shims and src paths needed by connector modules in tests."""

    dlp_module = types.ModuleType("security.dlp")
    secrets_module = types.ModuleType("security.secrets")
    keyvault_module = types.ModuleType("security.keyvault")

    dlp_module.redact_payload = lambda payload: payload
    secrets_module.resolve_secret = lambda value: value

    class DummyKeyVaultConfig:
        def __init__(self, vault_url: str | None = None) -> None:
            self.vault_url = vault_url

    class DummyKeyVaultClient:
        def __init__(self, _config: DummyKeyVaultConfig) -> None:
            return None

        def get_secret(self, _name: str) -> str | None:
            return None

        def set_secret(self, _name: str, _value: str) -> None:
            return None

    class DummyKeyVaultUnavailableError(Exception):
        pass

    keyvault_module.KeyVaultClient = DummyKeyVaultClient
    keyvault_module.KeyVaultConfig = DummyKeyVaultConfig
    keyvault_module.KeyVaultUnavailableError = DummyKeyVaultUnavailableError

    sys.modules.setdefault("security.dlp", dlp_module)
    sys.modules.setdefault("security.secrets", secrets_module)
    sys.modules.setdefault("security.keyvault", keyvault_module)

    src_paths = [SDK_PATH] + [path / "src" for path in CONNECTORS_ROOT.iterdir() if (path / "src").is_dir()]
    for path in src_paths:
        path_str = str(path.resolve())
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

    import contextlib
    import importlib
    import types as _types
    import http_client as http_client_module

    class _DummySpan:
        def set_attribute(self, *_args: object, **_kwargs: object) -> None:
            return None

        def set_status(self, *_args: object, **_kwargs: object) -> None:
            return None

        def record_exception(self, *_args: object, **_kwargs: object) -> None:
            return None

    class _DummyTracer:
        def start_span(self, *_args: object, **_kwargs: object) -> _DummySpan:
            return _DummySpan()

    @contextlib.contextmanager
    def _noop_use_span(span: _DummySpan, end_on_exit: bool = True) -> _DummySpan:
        yield span

    for module_name in ("http_client", "integrations.connectors.sdk.src.http_client"):
        module = importlib.import_module(module_name)
        module.tracer = _DummyTracer()
        module.trace.use_span = _noop_use_span
        module.SpanKind = _types.SimpleNamespace(CLIENT="client")


@dataclass
class ConnectorHarnessCase:
    connector_id: str
    connector_class: Any
    category: Any
    env_vars: dict[str, str]
    read_resource: str
    write_resource: str
    auth_path: str
    read_path: str
    write_path: str
    items_path: str | None


class SequenceTransport:
    """Mock transport with deterministic per-route response sequences."""

    def __init__(self, routes: dict[tuple[str, str], list[httpx.Response] | httpx.Response]) -> None:
        self.calls: dict[tuple[str, str], int] = {}
        self.requests: list[httpx.Request] = []

        def to_seq(value: list[httpx.Response] | httpx.Response) -> list[httpx.Response]:
            return value if isinstance(value, list) else [value]

        self._routes = {key: to_seq(value) for key, value in routes.items()}
        self.transport = httpx.MockTransport(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        self.requests.append(request)
        self.calls[key] = self.calls.get(key, 0) + 1
        if key not in self._routes:
            return httpx.Response(404, json={"error": "not found"})
        queue = self._routes[key]
        idx = min(self.calls[key] - 1, len(queue) - 1)
        return queue[idx]


def build_items_payload(items_path: str | None, items: list[dict[str, Any]]) -> dict[str, Any] | list[dict[str, Any]]:
    if not items_path:
        return items
    payload: dict[str, Any] = {}
    current = payload
    parts = items_path.split(".")
    for part in parts[:-1]:
        current[part] = {}
        current = current[part]
    current[parts[-1]] = items
    return payload


def assert_connector_contract(case: ConnectorHarnessCase) -> None:
    required_resources = case.connector_class.RESOURCE_PATHS
    assert case.read_resource in required_resources
    assert case.write_resource in required_resources
    assert case.connector_class.SUPPORTS_WRITE is True
    assert required_resources[case.write_resource].get("write_path")

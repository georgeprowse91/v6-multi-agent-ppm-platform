from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


class _Request:
    def __init__(self, *, tenant_id: str, live: bool, records: list[dict[str, object]], include_schema: bool = False) -> None:
        self.tenant_id = tenant_id
        self.live = live
        self.records = records
        self.include_schema = include_schema


class _HttpClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _load_router() -> types.ModuleType:
    module_name = "connectors.servicenow.src.router"
    sys.modules.pop(module_name, None)

    sync_router_stub = types.ModuleType("connectors.sdk.src.sync_router")
    sync_router_stub.InboundSyncRequest = object
    sync_router_stub.OutboundSyncRequest = object
    sync_router_stub.map_records = lambda *_args, **_kwargs: [{"id": "mapped-1"}]
    sys.modules[sync_router_stub.__name__] = sync_router_stub

    http_stub = types.ModuleType("connectors.sdk.src.http_client")
    http_stub.HttpClientError = _HttpClientError
    http_stub.HttpClient = lambda **_kwargs: object()
    sys.modules[http_stub.__name__] = http_stub

    main_stub = types.ModuleType("connectors.servicenow.src.main")
    main_stub.CONNECTOR_ROOT = Path(".")

    class _Config:
        @classmethod
        def from_env(cls, _manifest: dict, _rate: int):
            return types.SimpleNamespace(instance_url="https://example.com", rate_limit_per_minute=300)

    main_stub.ServiceNowConfig = _Config
    main_stub._build_token_manager = lambda _config, token_client=None: types.SimpleNamespace(get_access_token=lambda: "token")
    main_stub._build_api_client = lambda _config, _token: object()
    main_stub._request_with_refresh = lambda *_args, **_kwargs: types.SimpleNamespace(json=lambda: {"ok": True}, status_code=200)
    main_stub.run_sync = lambda *_args, **_kwargs: []
    sys.modules[main_stub.__name__] = main_stub

    return importlib.import_module(module_name)


def test_sync_outbound_dry_run_returns_consistent_shape() -> None:
    router = _load_router()

    response = router.sync_outbound(_Request(tenant_id="tenant-a", live=False, records=[{"id": "P-1"}]))

    assert response["status"] == "dry_run"
    assert response["sent_count"] == 0
    assert response["failed_count"] == 0
    assert response["errors"] == []


def test_sync_outbound_live_reports_partial_failures(monkeypatch) -> None:
    router = _load_router()
    monkeypatch.setattr(router, "map_records", lambda *_args, **_kwargs: [{"id": "ok-1"}, {"id": "bad-1"}])

    def _request(*_args, **kwargs):
        if kwargs["json"]["sys_id"] == "bad-1":
            raise router.HttpClientError("boom", status_code=400)
        return types.SimpleNamespace(json=lambda: {"result": "created"}, status_code=200)

    monkeypatch.setattr(router, "_request_with_refresh", _request)

    response = router.sync_outbound(_Request(tenant_id="tenant-a", live=True, records=[{"id": "P-1"}]))

    assert response["status"] == "partial_failure"
    assert response["sent_count"] == 1
    assert response["failed_count"] == 1
    assert len(response["errors"]) == 1


def test_sync_outbound_live_no_longer_501() -> None:
    router = _load_router()

    response = router.sync_outbound(_Request(tenant_id="tenant-a", live=True, records=[{"id": "P-1"}]))

    assert response["status"] == "sent"
    assert response["sent_count"] == 1
    assert response["failed_count"] == 0

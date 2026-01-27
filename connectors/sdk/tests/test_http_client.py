from __future__ import annotations

from typing import Any

import httpx

from connectors.sdk.src.http_client import HttpClient, HttpClientError, RetryConfig


def test_http_client_retries_transient_errors() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(500, json={"error": "oops"})
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = HttpClient(
        base_url="https://example.com",
        retry_config=RetryConfig(max_retries=2, backoff_factor=0.0),
        transport=transport,
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert len(calls) == 2


def test_http_client_offset_pagination() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("startAt", "0"))
        max_results = int(request.url.params.get("maxResults", "2"))
        values: list[dict[str, Any]] = [
            {"id": offset + 1},
            {"id": offset + 2},
        ]
        if offset >= 2:
            values = []
        return httpx.Response(
            200,
            json={
                "values": values[:max_results],
                "isLast": offset >= 2,
            },
        )

    transport = httpx.MockTransport(handler)
    client = HttpClient(
        base_url="https://example.com",
        retry_config=RetryConfig(max_retries=1, backoff_factor=0.0),
        transport=transport,
    )

    pages = list(
        client.paginate_offset(
            "/projects",
            params={},
            items_path="values",
            offset_param="startAt",
            limit_param="maxResults",
            limit=2,
            is_last_page=lambda data, items: bool(data.get("isLast")),
        )
    )

    assert [item["id"] for page in pages for item in page] == [1, 2]


def test_http_client_raises_structured_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    transport = httpx.MockTransport(handler)
    client = HttpClient(base_url="https://example.com", transport=transport)

    try:
        client.get("/bad")
    except HttpClientError as exc:
        assert exc.status_code == 400
        assert exc.response_json == {"error": "bad request"}
        assert exc.request_method == "GET"
        assert "https://example.com/bad" in (exc.request_url or "")
    else:
        raise AssertionError("Expected HttpClientError")

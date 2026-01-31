import httpx
import pytest

from web_search import search_web


class DummyResponse:
    def __init__(self, payload, status_error=None):
        self._payload = payload
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error

    def json(self):
        return self._payload


class DummyClient:
    def __init__(self, response):
        self._response = response
        self.last_request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, params=None, headers=None):
        self.last_request = {"url": url, "params": params, "headers": headers}
        return self._response


@pytest.mark.asyncio
async def test_search_web_returns_snippets(monkeypatch):
    payload = {
        "webPages": {
            "value": [
                {"name": "Guide", "snippet": "Best practice", "url": "https://example.com"},
                {"name": "Checklist", "snippet": "Regulatory steps", "url": "https://example.org"},
            ]
        }
    }
    dummy_client = DummyClient(DummyResponse(payload))

    monkeypatch.setenv("SEARCH_API_ENDPOINT", "https://search.example.com")
    monkeypatch.setenv("SEARCH_API_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: dummy_client)

    results = await search_web("test", result_limit=2)

    assert len(results) == 2
    assert "Guide" in results[0]
    assert "Checklist" in results[1]


@pytest.mark.asyncio
async def test_search_web_handles_errors(monkeypatch):
    dummy_client = DummyClient(DummyResponse({}, status_error=httpx.HTTPError("boom")))
    monkeypatch.setenv("SEARCH_API_ENDPOINT", "https://search.example.com")
    monkeypatch.setenv("SEARCH_API_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: dummy_client)

    results = await search_web("test", result_limit=2)

    assert results == []

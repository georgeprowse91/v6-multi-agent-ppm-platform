from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import httpx


@dataclass
class RetryConfig:
    max_retries: int = 3
    backoff_factor: float = 0.5
    retry_statuses: tuple[int, ...] = (429, 500, 502, 503, 504)


class RateLimiter:
    def __init__(self, rate_limit_per_minute: int | None) -> None:
        self._rate_limit_per_minute = rate_limit_per_minute
        self._last_request_at: float | None = None

    def wait(self) -> None:
        if not self._rate_limit_per_minute:
            return
        min_interval = 60.0 / self._rate_limit_per_minute
        now = time.monotonic()
        if self._last_request_at is None:
            self._last_request_at = now
            return
        elapsed = now - self._last_request_at
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_at = time.monotonic()


def _extract_items(data: dict[str, Any], path: str | list[str]) -> list[dict[str, Any]]:
    if isinstance(path, str):
        keys = [segment for segment in path.split(".") if segment]
    else:
        keys = path
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    if isinstance(current, list):
        return list(current)
    return []


class HttpClient:
    def __init__(
        self,
        base_url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
        rate_limit_per_minute: int | None = None,
        retry_config: RetryConfig | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            transport=transport,
        )
        self._retry = retry_config or RetryConfig()
        self._rate_limiter = RateLimiter(rate_limit_per_minute)

    @property
    def headers(self) -> dict[str, str]:
        return dict(self._client.headers)

    def close(self) -> None:
        self._client.close()

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        attempt = 0
        while True:
            self._rate_limiter.wait()
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.RequestError:
                if attempt >= self._retry.max_retries:
                    raise
                attempt += 1
                time.sleep(self._retry.backoff_factor * (2**(attempt - 1)))
                continue

            if response.status_code in self._retry.retry_statuses and attempt < self._retry.max_retries:
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    time.sleep(float(retry_after))
                else:
                    time.sleep(self._retry.backoff_factor * (2**attempt))
                attempt += 1
                continue

            response.raise_for_status()
            return response

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def paginate_offset(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None,
        items_path: str,
        offset_param: str,
        limit_param: str,
        limit: int,
        is_last_page: Callable[[dict[str, Any], list[dict[str, Any]]], bool] | None = None,
        max_pages: int | None = None,
    ) -> Iterable[list[dict[str, Any]]]:
        params = dict(params or {})
        offset = int(params.get(offset_param, 0))
        params[limit_param] = limit
        pages = 0
        while True:
            params[offset_param] = offset
            response = self.get(endpoint, params=params)
            data = response.json()
            items = _extract_items(data, items_path)
            yield items
            pages += 1
            if max_pages and pages >= max_pages:
                return
            if is_last_page and is_last_page(data, items):
                return
            if len(items) < limit:
                return
            offset += limit

    def paginate_continuation(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None,
        items_path: str,
        continuation_header: str = "x-ms-continuationtoken",
        continuation_param: str = "continuationToken",
        max_pages: int | None = None,
    ) -> Iterable[list[dict[str, Any]]]:
        params = dict(params or {})
        continuation: str | None = None
        pages = 0
        while True:
            if continuation:
                params[continuation_param] = continuation
            response = self.get(endpoint, params=params)
            data = response.json()
            items = _extract_items(data, items_path)
            yield items
            pages += 1
            if max_pages and pages >= max_pages:
                return
            continuation = response.headers.get(continuation_header)
            if not continuation:
                return


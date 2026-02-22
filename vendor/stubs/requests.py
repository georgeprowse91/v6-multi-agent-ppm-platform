"""Minimal requests compatibility layer."""

from __future__ import annotations

import json
import urllib.request


class Response:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def get(url: str, timeout: float | None = None):
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return Response(resp.status, resp.read().decode("utf-8"))


def post(url: str, json: dict | None = None, timeout: float | None = None):
    data = None if json is None else __import__("json").dumps(json).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return Response(resp.status, resp.read().decode("utf-8"))

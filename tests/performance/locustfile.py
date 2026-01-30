from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Any

import yaml
from locust import HttpUser, task
from locust.wait_time import constant_pacing, between

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


@dataclass(frozen=True)
class Endpoint:
    name: str
    method: str
    path: str
    weight: int = 1
    json_body: dict[str, Any] | None = None


def load_config() -> dict[str, Any]:
    config_path = os.getenv("PERF_CONFIG", DEFAULT_CONFIG_PATH)
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


CONFIG = load_config()
ENDPOINTS = [
    Endpoint(
        name=item["name"],
        method=item.get("method", "GET"),
        path=item["path"],
        weight=int(item.get("weight", 1)),
        json_body=item.get("json"),
    )
    for item in CONFIG.get("endpoints", [])
]

REQUEST_RATE = CONFIG.get("request_rate_per_user")
HEADERS = CONFIG.get("headers", {})


class PerformanceUser(HttpUser):
    host = CONFIG.get("host")
    if REQUEST_RATE:
        wait_time = constant_pacing(1 / float(REQUEST_RATE))
    else:
        wait_time = between(0.5, 1.5)

    @task
    def exercise_endpoint(self) -> None:
        if not ENDPOINTS:
            return

        endpoint = random.choices(ENDPOINTS, weights=[e.weight for e in ENDPOINTS], k=1)[0]
        method = endpoint.method.lower()
        payload = endpoint.json_body

        with self.client.request(
            method,
            endpoint.path,
            json=payload,
            name=endpoint.name,
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code >= 400:
                response.failure(f"HTTP {response.status_code}")

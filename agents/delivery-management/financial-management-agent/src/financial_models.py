"""Financial Management Agent - Infrastructure models and service clients."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


class ExchangeRateProvider:
    """Exchange rate provider with caching and optional API fetch."""

    def __init__(self, fixture_path: Path, ttl_seconds: int, api_url: str | None = None):
        self.fixture_path = fixture_path
        self.ttl_seconds = ttl_seconds
        self.api_url = api_url
        self._cache: dict[str, Any] | None = None
        self._last_loaded: datetime | None = None

    async def get_rates(self) -> dict[str, Any]:
        if self._cache and self._last_loaded:
            age = (datetime.now(timezone.utc) - self._last_loaded).total_seconds()
            if age < self.ttl_seconds:
                return self._cache

        if self.api_url:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.api_url)
                response.raise_for_status()
                data = response.json()
        else:
            data = json.loads(self.fixture_path.read_text())

        self._cache = {
            "base": data.get("base", "AUD"),
            "rates": data.get("rates", {}),
            "as_of": data.get("as_of", datetime.now(timezone.utc).isoformat()),
        }
        self._last_loaded = datetime.now(timezone.utc)
        return self._cache


class TaxRateProvider:
    """Tax rate provider with caching and optional API fetch."""

    def __init__(self, fixture_path: Path, ttl_seconds: int, api_url: str | None = None):
        self.fixture_path = fixture_path
        self.ttl_seconds = ttl_seconds
        self.api_url = api_url
        self._cache: dict[str, Any] | None = None
        self._last_loaded: datetime | None = None

    async def get_rates(self) -> dict[str, Any]:
        if self._cache and self._last_loaded:
            age = (datetime.now(timezone.utc) - self._last_loaded).total_seconds()
            if age < self.ttl_seconds:
                return self._cache

        if self.api_url:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.api_url)
                response.raise_for_status()
                data = response.json()
        else:
            data = json.loads(self.fixture_path.read_text())

        self._cache = {
            "default_rate": data.get("default_rate", 0),
            "default_region": data.get("default_region", "AU"),
            "rates": data.get("rates", {}),
            "as_of": data.get("as_of", datetime.now(timezone.utc).isoformat()),
        }
        self._last_loaded = datetime.now(timezone.utc)
        return self._cache


class DataFactoryPipelineManager:
    """Lightweight wrapper to schedule Data Factory pipelines."""

    def __init__(self, data_factory_client: Any | None = None) -> None:
        self.data_factory_client = data_factory_client

    async def schedule_pipeline(self, pipeline_name: str, parameters: dict[str, Any]) -> str:
        if self.data_factory_client and hasattr(self.data_factory_client, "pipelines"):
            response = self.data_factory_client.pipelines.create_run(
                pipeline_name, parameters=parameters
            )
            return getattr(response, "run_id", "unknown")
        return f"run-{pipeline_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

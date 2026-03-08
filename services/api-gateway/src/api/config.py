from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

from common.env_validation import (  # noqa: E402
    build_validation_diagnostics,
    format_validation_report,
    reject_placeholder_secrets,
)


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    environment: Literal["development", "dev", "staging", "production"] = "development"
    llm_provider: str = "mock"
    demo_mode: bool = False
    llm_mock_response_path: str = "/app/examples/demo-scenarios/quickstart-llm-response.json"
    auth_dev_mode: bool = False
    auth_dev_roles: str = "PMO_ADMIN"
    auth_dev_tenant_id: str = "dev-tenant-local"

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str | None = None

    search_api_endpoint: str | None = None
    search_api_key: str | None = None
    search_api_min_interval: float | None = None
    search_result_limit: int | None = None

    @field_validator(
        "azure_openai_endpoint",
        "azure_openai_api_key",
        "azure_openai_deployment",
        "search_api_endpoint",
        "search_api_key",
        "search_api_min_interval",
        "search_result_limit",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def validate_startup_config() -> Settings:
    try:
        settings = get_settings()
    except ValidationError as exc:
        diagnostics = build_validation_diagnostics(exc)
        raise RuntimeError(format_validation_report("api-gateway", diagnostics)) from exc
    if settings.auth_dev_mode and settings.environment in ("production", "staging"):
        raise RuntimeError(
            "AUTH_DEV_MODE must not be enabled in production or staging. "
            "Set AUTH_DEV_MODE=false in the environment configuration."
        )
    reject_placeholder_secrets(
        service_name="api-gateway",
        environment=settings.environment,
        secret_vars={"DATABASE_URL": settings.database_url},
    )
    return settings

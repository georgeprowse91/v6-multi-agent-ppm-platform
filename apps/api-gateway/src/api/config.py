from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
COMMON_ROOT = REPO_ROOT / "packages" / "common" / "src"
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from common.env_validation import build_validation_diagnostics, format_validation_report


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", env="LOG_LEVEL"
    )
    environment: Literal["development", "dev", "staging", "production"] = Field(
        "development", env="ENVIRONMENT"
    )
    llm_provider: str = Field("mock", env="LLM_PROVIDER")
    demo_mode: bool = Field(False, env="DEMO_MODE")
    llm_mock_response_path: str = Field(
        "/app/examples/demo-scenarios/quickstart-llm-response.json", env="LLM_MOCK_RESPONSE_PATH"
    )
    auth_dev_mode: bool = Field(True, env="AUTH_DEV_MODE")
    auth_dev_roles: str = Field("PMO_ADMIN", env="AUTH_DEV_ROLES")
    auth_dev_tenant_id: str = Field("dev-tenant-local", env="AUTH_DEV_TENANT_ID")

    azure_openai_endpoint: str | None = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str | None = Field(default=None, env="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str | None = Field(default=None, env="AZURE_OPENAI_DEPLOYMENT")

    search_api_endpoint: str | None = Field(default=None, env="SEARCH_API_ENDPOINT")
    search_api_key: str | None = Field(default=None, env="SEARCH_API_KEY")
    search_api_min_interval: float | None = Field(default=None, env="SEARCH_API_MIN_INTERVAL")
    search_result_limit: int | None = Field(default=None, env="SEARCH_RESULT_LIMIT")

    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), str(REPO_ROOT / ".env.example")),
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def validate_startup_config() -> Settings:
    try:
        return get_settings()
    except ValidationError as exc:
        diagnostics = build_validation_diagnostics(exc)
        raise RuntimeError(format_validation_report("api-gateway", diagnostics)) from exc

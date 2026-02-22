from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
COMMON_ROOT = REPO_ROOT / "packages" / "common" / "src"
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from common.env_validation import build_validation_diagnostics, format_validation_report


class Settings(BaseSettings):
    environment: Literal["development", "dev", "staging", "production"] = Field(
        "development", env="ENVIRONMENT"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", env="LOG_LEVEL"
    )
    demo_mode: bool = Field(False, env="DEMO_MODE")
    orchestration_state_backend: Literal["db", "memory"] = Field(
        "db", env="ORCHESTRATION_STATE_BACKEND"
    )
    database_url: str = Field(..., env="DATABASE_URL")
    workflow_engine_url: str = Field(..., env="WORKFLOW_ENGINE_URL")
    auth_dev_mode: bool = Field(False, env="AUTH_DEV_MODE")
    auth_dev_roles: str = Field("PMO_ADMIN", env="AUTH_DEV_ROLES")
    auth_dev_tenant_id: str = Field("dev-tenant-local", env="AUTH_DEV_TENANT_ID")

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
        raise RuntimeError(format_validation_report("orchestration-service", diagnostics)) from exc
    if settings.auth_dev_mode and settings.environment == "production":
        raise RuntimeError(
            "AUTH_DEV_MODE must not be enabled in production. "
            "Set AUTH_DEV_MODE=false in the production environment."
        )
    return settings

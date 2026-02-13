from __future__ import annotations

from functools import lru_cache
import sys
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
    workflow_engine_url: str = Field(..., env="WORKFLOW_ENGINE_URL")
    api_gateway_url: str = Field(..., env="API_GATEWAY_URL")

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
        raise RuntimeError(format_validation_report("workflow-engine", diagnostics)) from exc

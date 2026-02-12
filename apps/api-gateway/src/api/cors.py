from __future__ import annotations

import os

from common.exceptions import ValidationError

DEFAULT_CORS_ORIGINS_BY_ENV: dict[str, list[str]] = {
    "local": ["http://localhost:3000", "http://localhost:8501", "http://localhost:8000"],
    "development": ["http://localhost:3000", "http://localhost:8501", "http://localhost:8000"],
    "dev": ["http://localhost:3000", "http://localhost:8501", "http://localhost:8000"],
    "test": ["http://localhost:3000"],
    "staging": ["https://staging.ppm.example.com"],
    "production": ["https://ppm.example.com"],
    "prod": ["https://ppm.example.com"],
}
ALLOWED_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_CORS_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "X-Tenant-ID",
    "X-Dev-User",
    "X-Webhook-Secret",
    "X-Webhook-Signature",
]


def get_allowed_origins(current_environment: str) -> list[str]:
    env_key = current_environment.strip().lower()
    origins_env_key = f"CORS_ALLOWED_ORIGINS_{env_key.upper()}"
    configured_origins = os.getenv(origins_env_key)

    if configured_origins is None:
        configured_origins = os.getenv("CORS_ALLOWED_ORIGINS")
    if configured_origins is None:
        configured_origins = os.getenv("ALLOWED_ORIGINS")
    if configured_origins is None:
        return DEFAULT_CORS_ORIGINS_BY_ENV.get(env_key, DEFAULT_CORS_ORIGINS_BY_ENV["development"])

    configured_origins = configured_origins.strip()
    if configured_origins == "*":
        raise ValidationError(
            "Wildcard CORS origins are not permitted when credentials are enabled. Configure explicit trusted origins instead."
        )

    origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    if not origins:
        raise ValidationError(
            f"{origins_env_key} is empty. Configure at least one explicit trusted origin."
        )
    return origins

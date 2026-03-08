"""
Zoom Connector Implementation.

Supports:
- OAuth2 authentication
- Reading meetings and webinars
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from connector_secrets import fetch_keyvault_secret, resolve_secret  # noqa: E402
from rest_connector import OAuth2RestConnector  # noqa: E402


class ZoomConnector(OAuth2RestConnector):
    CONNECTOR_ID = "zoom"
    CONNECTOR_NAME = "Zoom"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = False

    INSTANCE_URL_ENV = "ZOOM_API_URL"
    CLIENT_ID_ENV = "ZOOM_CLIENT_ID"
    CLIENT_SECRET_ENV = "ZOOM_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "ZOOM_REFRESH_TOKEN"
    TOKEN_URL_ENV = "ZOOM_TOKEN_URL"
    DEFAULT_TOKEN_URL = "https://zoom.us/oauth/token"
    SCOPES_ENV = "ZOOM_SCOPES"
    KEYVAULT_URL_ENV = "ZOOM_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "ZOOM_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "ZOOM_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "ZOOM_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/users/me"
    RESOURCE_PATHS = {
        "meetings": {"path": "/users/me/meetings", "items_path": "meetings"},
        "webinars": {"path": "/users/me/webinars", "items_path": "webinars"},
    }
    SCHEMA = {
        "meetings": {"id": "string", "topic": "string"},
        "webinars": {"id": "string", "topic": "string"},
    }

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        if not instance_url:
            instance_url = "https://api.zoom.us/v2"
        keyvault_url = resolve_secret(os.getenv(self.KEYVAULT_URL_ENV))
        client_id = resolve_secret(os.getenv(self.CLIENT_ID_ENV))
        client_secret = resolve_secret(os.getenv(self.CLIENT_SECRET_ENV))
        refresh_token = resolve_secret(os.getenv(self.REFRESH_TOKEN_ENV))
        client_id_secret = resolve_secret(os.getenv(self.CLIENT_ID_SECRET_ENV))
        client_secret_secret = resolve_secret(os.getenv(self.CLIENT_SECRET_SECRET_ENV))
        refresh_token_secret = resolve_secret(os.getenv(self.REFRESH_TOKEN_SECRET_ENV))
        client_id = (
            fetch_keyvault_secret(keyvault_url, client_id_secret) if client_id_secret else client_id
        ) or client_id
        client_secret = (
            fetch_keyvault_secret(keyvault_url, client_secret_secret)
            if client_secret_secret
            else client_secret
        ) or client_secret
        refresh_token = (
            fetch_keyvault_secret(keyvault_url, refresh_token_secret)
            if refresh_token_secret
            else refresh_token
        ) or refresh_token
        if not client_id or not client_secret or not refresh_token:
            raise ValueError(
                f"{self.CLIENT_ID_ENV}, {self.CLIENT_SECRET_ENV}, and {self.REFRESH_TOKEN_ENV} are required"
            )
        return instance_url, client_id, client_secret, refresh_token

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)

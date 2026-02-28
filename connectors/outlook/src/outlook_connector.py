"""
Outlook Connector Implementation.

Supports:
- OAuth2 authentication via Microsoft Graph
- Reading calendar events and calendars
- Writing calendar events
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_COMMON_SRC = _REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from rest_connector import OAuth2RestConnector  # noqa: E402
from connector_secrets import resolve_secret  # noqa: E402

DEFAULT_GRAPH_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


class OutlookConnector(OAuth2RestConnector):
    CONNECTOR_ID = "outlook"
    CONNECTOR_NAME = "Outlook"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = True
    IDEMPOTENCY_FIELDS = ("id", "iCalUId", "external_id")
    CONFLICT_TIMESTAMP_FIELD = "lastModifiedDateTime"

    INSTANCE_URL_ENV = "OUTLOOK_API_URL"
    CLIENT_ID_ENV = "OUTLOOK_CLIENT_ID"
    CLIENT_SECRET_ENV = "OUTLOOK_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "OUTLOOK_REFRESH_TOKEN"
    TOKEN_URL_ENV = "OUTLOOK_TOKEN_URL"
    DEFAULT_TOKEN_URL = DEFAULT_TOKEN_URL
    SCOPES_ENV = "OUTLOOK_SCOPES"
    KEYVAULT_URL_ENV = "OUTLOOK_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "OUTLOOK_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "OUTLOOK_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "OUTLOOK_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/me/events"
    AUTH_TEST_PARAMS = {"$top": 1}
    RESOURCE_PATHS = {
        "events": {
            "path": "/me/events",
            "items_path": "value",
            "write_path": "/me/events",
            "write_method": "POST",
        },
        "calendar_view": {"path": "/me/calendarView", "items_path": "value"},
        "calendars": {"path": "/me/calendars", "items_path": "value"},
    }
    SCHEMA = {
        "events": {"id": "string", "subject": "string"},
        "calendar_view": {"id": "string", "subject": "string"},
        "calendars": {"id": "string", "name": "string"},
    }

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        if not instance_url:
            instance_url = DEFAULT_GRAPH_URL
        client_id = resolve_secret(os.getenv(self.CLIENT_ID_ENV))
        client_secret = resolve_secret(os.getenv(self.CLIENT_SECRET_ENV))
        refresh_token = resolve_secret(os.getenv(self.REFRESH_TOKEN_ENV))
        if not client_id or not client_secret or not refresh_token:
            raise ValueError(
                f"{self.CLIENT_ID_ENV}, {self.CLIENT_SECRET_ENV}, and {self.REFRESH_TOKEN_ENV} are required"
            )
        return instance_url, client_id, client_secret, refresh_token

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)

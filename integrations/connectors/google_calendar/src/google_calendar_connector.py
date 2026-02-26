"""
Google Calendar Connector Implementation.

Supports:
- OAuth2 authentication
- Reading calendar events
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

DEFAULT_CALENDAR_URL = "https://www.googleapis.com/calendar/v3"
DEFAULT_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleCalendarConnector(OAuth2RestConnector):
    CONNECTOR_ID = "google_calendar"
    CONNECTOR_NAME = "Google Calendar"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = True

    INSTANCE_URL_ENV = "GOOGLE_CALENDAR_BASE_URL"
    CLIENT_ID_ENV = "GOOGLE_CALENDAR_CLIENT_ID"
    CLIENT_SECRET_ENV = "GOOGLE_CALENDAR_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "GOOGLE_CALENDAR_REFRESH_TOKEN"
    TOKEN_URL_ENV = "GOOGLE_CALENDAR_TOKEN_URL"
    DEFAULT_TOKEN_URL = DEFAULT_TOKEN_URL
    SCOPES_ENV = "GOOGLE_CALENDAR_SCOPES"
    KEYVAULT_URL_ENV = "GOOGLE_CALENDAR_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "GOOGLE_CALENDAR_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "GOOGLE_CALENDAR_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "GOOGLE_CALENDAR_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/calendars/primary/events"
    AUTH_TEST_PARAMS = {"maxResults": 1}
    RESOURCE_PATHS = {
        "events": {
            "path": "/calendars/primary/events",
            "items_path": "items",
            "write_path": "/calendars/primary/events",
            "write_method": "POST",
        },
        "calendars": {"path": "/users/me/calendarList", "items_path": "items"},
    }
    SCHEMA = {
        "events": {"id": "string", "summary": "string"},
        "calendars": {"id": "string", "summary": "string"},
    }

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        if not instance_url:
            instance_url = DEFAULT_CALENDAR_URL
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

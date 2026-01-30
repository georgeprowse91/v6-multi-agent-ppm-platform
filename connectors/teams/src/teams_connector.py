"""
Microsoft Teams Connector Implementation.

Supports:
- OAuth2 authentication
- Reading teams and channels
- Writing messages
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from base_connector import ConnectorCategory, ConnectorConfig
from rest_connector import OAuth2RestConnector
from secrets import resolve_secret

DEFAULT_TEAMS_URL = "https://graph.microsoft.com/v1.0"


class TeamsConnector(OAuth2RestConnector):
    CONNECTOR_ID = "teams"
    CONNECTOR_NAME = "Microsoft Teams"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COLLABORATION
    SUPPORTS_WRITE = True

    INSTANCE_URL_ENV = "TEAMS_API_URL"
    CLIENT_ID_ENV = "TEAMS_CLIENT_ID"
    CLIENT_SECRET_ENV = "TEAMS_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "TEAMS_REFRESH_TOKEN"
    TOKEN_URL_ENV = "TEAMS_TOKEN_URL"
    DEFAULT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    SCOPES_ENV = "TEAMS_SCOPES"

    AUTH_TEST_ENDPOINT = "/me/joinedTeams"
    AUTH_TEST_PARAMS = {"$top": 1}
    RESOURCE_PATHS = {
        "teams": {"path": "/me/joinedTeams", "items_path": "value"},
        "channels": {"path": "/teams/{team_id}/channels", "items_path": "value"},
        "messages": {
            "path": "/teams/{team_id}/channels/{channel_id}/messages",
            "items_path": "value",
            "write_path": "/teams/{team_id}/channels/{channel_id}/messages",
            "write_method": "POST",
        },
    }
    SCHEMA = {
        "teams": {"id": "string", "displayName": "string"},
        "channels": {"id": "string", "displayName": "string"},
        "messages": {"id": "string", "body": "string"},
    }

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        if not instance_url:
            instance_url = DEFAULT_TEAMS_URL
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

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from connectors.sdk.src.http_client import HttpClient, HttpClientError


@dataclass
class OAuthToken:
    access_token: str
    refresh_token: str | None
    expires_at: float | None


class OAuth2TokenManager:
    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        scope: str | None = None,
        http_client: HttpClient | None = None,
        expiry_buffer_seconds: int = 60,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._scope = scope
        self._http_client = http_client
        self._expiry_buffer_seconds = expiry_buffer_seconds
        self._token: OAuthToken | None = None

    def _build_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        if self._scope:
            payload["scope"] = self._scope
        return payload

    def refresh(self) -> OAuthToken:
        client = self._http_client or HttpClient(base_url="https://localhost")
        response = client.post(self._token_url, data=self._build_payload())
        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise HttpClientError(
                "OAuth token refresh failed: access_token missing",
                status_code=response.status_code,
                response_json=data,
            )
        refresh_token = data.get("refresh_token", self._refresh_token)
        expires_in = data.get("expires_in")
        expires_at = None
        if isinstance(expires_in, (int, float)):
            expires_at = time.time() + float(expires_in) - self._expiry_buffer_seconds
        token = OAuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        self._token = token
        return token

    def get_access_token(self) -> str:
        if not self._token:
            return self.refresh().access_token
        if self._token.expires_at and time.time() >= self._token.expires_at:
            return self.refresh().access_token
        return self._token.access_token

"""
SharePoint Connector Implementation.

Supports:
- OAuth2 authentication
- Reading site lists and documents
- Writing documents (metadata updates)
- Cross-system search via SharePoint Search REST API
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig, ConnectorSearchResult  # noqa: E402
from rest_connector import OAuth2RestConnector  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


class SharePointConnector(OAuth2RestConnector):
    CONNECTOR_ID = "sharepoint"
    CONNECTOR_NAME = "SharePoint"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.DOC_MGMT
    SUPPORTS_WRITE = True

    INSTANCE_URL_ENV = "SHAREPOINT_SITE_URL"
    CLIENT_ID_ENV = "SHAREPOINT_CLIENT_ID"
    CLIENT_SECRET_ENV = "SHAREPOINT_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "SHAREPOINT_REFRESH_TOKEN"
    TOKEN_URL_ENV = "SHAREPOINT_TOKEN_URL"
    DEFAULT_TOKEN_URL = DEFAULT_TOKEN_URL
    SCOPES_ENV = "SHAREPOINT_SCOPES"
    KEYVAULT_URL_ENV = "SHAREPOINT_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "SHAREPOINT_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "SHAREPOINT_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "SHAREPOINT_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/_api/web"
    RESOURCE_PATHS = {
        "lists": {"path": "/_api/web/lists", "items_path": "value"},
        "documents": {
            "path": "/_api/web/lists/getbytitle('Documents')/items",
            "items_path": "value",
            "write_path": "/_api/web/lists/getbytitle('Documents')/items",
            "write_method": "POST",
        },
    }
    SCHEMA = {
        "lists": {"Id": "string", "Title": "string"},
        "documents": {"Id": "string", "Title": "string"},
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)

    def search(
        self,
        query: str,
        *,
        resource_types: list[str] | None = None,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[ConnectorSearchResult]:
        """Search SharePoint using the REST search API."""
        if not query or not query.strip():
            return []
        if not self._authenticated and not self.authenticate():
            return []

        results: list[ConnectorSearchResult] = []

        try:
            escaped = query.replace("'", "''")
            response = self._request(
                "GET",
                "/_api/search/query",
                params={"querytext": f"'{escaped}'", "rowlimit": limit},
            )
            data = response.json()
            rows = (
                data.get("PrimaryQueryResult", {})
                .get("RelevantResults", {})
                .get("Table", {})
                .get("Rows", [])
            )
            for row in rows:
                cells = {
                    cell.get("Key"): cell.get("Value")
                    for cell in row.get("Cells", [])
                    if cell.get("Key")
                }
                results.append(
                    ConnectorSearchResult(
                        id=str(cells.get("UniqueId") or cells.get("DocId", "")),
                        title=cells.get("Title") or cells.get("FileName", ""),
                        snippet=cells.get("HitHighlightedSummary", "")[:200],
                        source_system="sharepoint",
                        resource_type="documents",
                        url=cells.get("Path") or cells.get("OriginalPath"),
                        score=float(cells.get("Rank", 0)) / 100.0 if cells.get("Rank") else 0.8,
                        updated_at=cells.get("LastModifiedTime"),
                        metadata=cells,
                    )
                )
        except Exception:
            logger.warning("SharePoint search failed for query: %s", query)
            return super().search(
                query, resource_types=resource_types, limit=limit, filters=filters
            )

        return results[:limit]

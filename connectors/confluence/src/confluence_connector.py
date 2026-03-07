"""
Confluence Connector Implementation.

Supports:
- Basic authentication (email + API token)
- Reading spaces and pages
- Writing pages
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

import logging
from typing import Any

from base_connector import ConnectorCategory, ConnectorConfig, ConnectorSearchResult  # noqa: E402
from rest_connector import BasicAuthRestConnector  # noqa: E402

logger = logging.getLogger(__name__)


class ConfluenceConnector(BasicAuthRestConnector):
    CONNECTOR_ID = "confluence"
    CONNECTOR_NAME = "Confluence"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.DOC_MGMT
    SUPPORTS_WRITE = True

    INSTANCE_URL_ENV = "CONFLUENCE_URL"
    USERNAME_ENV = "CONFLUENCE_EMAIL"
    PASSWORD_ENV = "CONFLUENCE_API_TOKEN"
    AUTH_TEST_ENDPOINT = "/wiki/rest/api/space"
    AUTH_TEST_PARAMS = {"limit": 1}
    RESOURCE_PATHS = {
        "spaces": {"path": "/wiki/rest/api/space", "items_path": "results"},
        "pages": {
            "path": "/wiki/rest/api/content",
            "items_path": "results",
            "write_path": "/wiki/rest/api/content",
        },
    }
    SCHEMA = {
        "spaces": {"id": "string", "key": "string", "name": "string"},
        "pages": {"id": "string", "title": "string", "type": "string"},
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
        """Search Confluence using the CQL search API."""
        if not query or not query.strip():
            return []
        if not self._authenticated and not self.authenticate():
            return []

        results: list[ConnectorSearchResult] = []
        escaped = query.replace('"', '\\"')
        cql = f'text ~ "{escaped}" OR title ~ "{escaped}"'
        space_key = (filters or {}).get("space_key")
        if space_key:
            cql = f'space = "{space_key}" AND ({cql})'

        try:
            response = self._request(
                "GET",
                "/wiki/rest/api/content/search",
                params={"cql": cql, "limit": limit, "expand": "space,version"},
            )
            data = response.json()
            for item in data.get("results", []):
                space = item.get("space", {})
                version = item.get("version", {})
                instance_url = self.config.instance_url or ""
                links = item.get("_links", {})
                web_ui = links.get("webui", "")
                url = f"{instance_url}/wiki{web_ui}" if web_ui else None
                results.append(
                    ConnectorSearchResult(
                        id=str(item.get("id", "")),
                        title=item.get("title", ""),
                        snippet=f"{item.get('type', 'page')} · {space.get('name', '')} · v{version.get('number', '?')}",
                        source_system="confluence",
                        resource_type="pages",
                        url=url,
                        score=1.0,
                        updated_at=version.get("when"),
                        metadata={
                            "id": item.get("id"),
                            "title": item.get("title"),
                            "type": item.get("type"),
                            "space_key": space.get("key"),
                            "space_name": space.get("name"),
                            "version": version.get("number"),
                        },
                    )
                )
        except Exception:
            logger.warning("Confluence search failed for query: %s", query)

        return results[:limit]

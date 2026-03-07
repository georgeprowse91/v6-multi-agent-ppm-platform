"""
Workday Connector Implementation.

Supports:
- OAuth2 authentication
- Reading worker, position, and skill profile data
- Skill profile extraction and structured taxonomy mapping
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from rest_connector import OAuth2RestConnector  # noqa: E402
from mcp_client import MCPClient, MCPClientError  # noqa: E402
try:
    from .mappers import map_from_mcp_response, map_to_mcp_params
except ImportError:
    import importlib.util as _ilu
    _mappers_spec = _ilu.spec_from_file_location(
        "workday_mappers", Path(__file__).with_name("mappers.py"),
    )
    _mappers_mod = _ilu.module_from_spec(_mappers_spec)
    _mappers_spec.loader.exec_module(_mappers_mod)
    map_from_mcp_response = _mappers_mod.map_from_mcp_response
    map_to_mcp_params = _mappers_mod.map_to_mcp_params

DEFAULT_TOKEN_URL = "https://wd3-impl-services1.workday.com/ccx/oauth2/token"

logger = logging.getLogger(__name__)


class WorkdayConnector(OAuth2RestConnector):
    CONNECTOR_ID = "workday"
    CONNECTOR_NAME = "Workday"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.HRIS
    SUPPORTS_WRITE = True
    IDEMPOTENCY_FIELDS = ("id", "worker_id", "position_id")
    CONFLICT_TIMESTAMP_FIELD = "updated_at"

    INSTANCE_URL_ENV = "WORKDAY_API_URL"
    CLIENT_ID_ENV = "WORKDAY_CLIENT_ID"
    CLIENT_SECRET_ENV = "WORKDAY_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "WORKDAY_REFRESH_TOKEN"
    TOKEN_URL_ENV = "WORKDAY_TOKEN_URL"
    DEFAULT_TOKEN_URL = DEFAULT_TOKEN_URL
    SCOPES_ENV = "WORKDAY_SCOPES"
    KEYVAULT_URL_ENV = "WORKDAY_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "WORKDAY_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "WORKDAY_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "WORKDAY_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/ccx/api/v1/workers"
    AUTH_TEST_PARAMS = {"limit": 1}
    RESOURCE_PATHS = {
        "workers": {"path": "/ccx/api/v1/workers", "items_path": "data", "write_path": "/ccx/api/v1/workers", "write_method": "POST"},
        "positions": {"path": "/ccx/api/v1/positions", "items_path": "data", "write_path": "/ccx/api/v1/positions", "write_method": "POST"},
        "skills": {"path": "/ccx/api/v1/workers", "items_path": "data"},
        "skill_profiles": {"path": "/staffing/v6/workers", "items_path": "data"},
    }
    SCHEMA = {
        "workers": {"id": "string", "name": "string", "status": "string"},
        "positions": {"id": "string", "title": "string"},
        "skills": {"worker_id": "string", "skills": "array"},
        "skill_profiles": {"worker_id": "string", "skill_id": "string", "name": "string", "proficiency_level": "integer", "category": "string"},
    }

    # Workday proficiency level → numeric 1-5 mapping
    _PROFICIENCY_MAP: dict[str, int] = {
        "beginner": 1,
        "basic": 1,
        "developing": 2,
        "intermediate": 2,
        "proficient": 3,
        "advanced": 3,
        "expert": 4,
        "mastery": 5,
        "thought_leader": 5,
    }

    # Workday skill group → structured taxonomy category
    _SKILL_GROUP_CATEGORY_MAP: dict[str, str] = {
        "technology": "technical",
        "technical": "technical",
        "programming": "technical",
        "engineering": "technical",
        "management": "leadership",
        "leadership": "leadership",
        "business": "domain",
        "industry": "domain",
        "finance": "domain",
        "methodology": "methodology",
        "agile": "methodology",
        "tool": "tool",
        "software": "tool",
        "language": "language",
        "certification": "certification",
        "communication": "soft_skill",
        "interpersonal": "soft_skill",
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)
        self._mcp_client: MCPClient | None = None
        self._mcp_tool_map = {
            "list_workers": "workday.listWorkers",
            "list_positions": "workday.listPositions",
            **(config.mcp_tool_map or {}),
        }

    def _build_mcp_client(self) -> MCPClient:
        if self._mcp_client:
            return self._mcp_client
        if not self.config.mcp_server_url:
            raise ValueError("Workday MCP server URL is required")
        self._mcp_client = MCPClient(
            mcp_server_id=self.config.mcp_server_id or self.CONNECTOR_ID,
            mcp_server_url=self.config.mcp_server_url,
            config=self.config,
        )
        return self._mcp_client

    def _run_mcp(self, coroutine: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()

    def _should_use_mcp(self, tool_key: str) -> bool:
        if not self.config.prefer_mcp:
            return False
        if not self.config.mcp_server_url:
            return False
        if not self.config.is_mcp_enabled_for(tool_key):
            return False
        return True

    def _list_records_via_mcp(
        self,
        *,
        resource_type: str,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        rest_call: Any,
    ) -> list[dict[str, Any]]:
        tool_key = f"list_{resource_type}"
        tool_name = self._mcp_tool_map.get(tool_key)
        if not self._should_use_mcp(tool_key):
            return rest_call()
        if not tool_name:
            logger.warning(
                "MCP tool mapping missing for %s; falling back to REST for Workday %s.",
                tool_key,
                resource_type,
            )
            return rest_call()
        params = map_to_mcp_params(
            "list",
            {
                "resource_type": resource_type,
                "filters": filters or {},
                "limit": limit,
                "offset": offset,
            },
        )
        try:
            client = self._build_mcp_client()
            payload = self._run_mcp(client.invoke_tool(tool_name, params))
            return map_from_mcp_response("list", payload)
        except (MCPClientError, ValueError) as exc:
            logger.warning(
                "MCP %s failed for Workday connector; falling back to REST. Error: %s",
                tool_key,
                exc,
            )
            return rest_call()

    def read(
        self,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if resource_type in ("skills", "skill_profiles"):
            return self.read_skill_profiles(filters=filters, limit=limit, offset=offset)
        return self._list_records_via_mcp(
            resource_type=resource_type,
            filters=filters,
            limit=limit,
            offset=offset,
            rest_call=lambda: OAuth2RestConnector.read(self, resource_type, filters=filters, limit=limit, offset=offset),
        )

    def read_skill_profiles(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Extract skill profiles from Workday worker data.

        Reads worker records and extracts embedded skill/competency data,
        mapping Workday's proficiency levels and skill groups to the
        platform's structured skills taxonomy.

        Returns a list of structured skill records per worker.
        """
        workers = self._list_records_via_mcp(
            resource_type="workers",
            filters=filters,
            limit=limit,
            offset=offset,
            rest_call=lambda: OAuth2RestConnector.read(
                self, "workers", filters=filters, limit=limit, offset=offset,
            ),
        )

        skill_records: list[dict[str, Any]] = []
        for worker in workers:
            worker_id = worker.get("id") or worker.get("worker_id", "")
            worker_name = worker.get("name", "")
            raw_skills = (
                worker.get("skills", [])
                or worker.get("competencies", [])
                or worker.get("skillProfile", {}).get("skills", [])
            )

            if isinstance(raw_skills, list):
                for raw_skill in raw_skills:
                    skill_entry = self._map_workday_skill(raw_skill, worker_id)
                    if skill_entry:
                        skill_records.append(skill_entry)
            elif isinstance(raw_skills, dict):
                skill_entry = self._map_workday_skill(raw_skills, worker_id)
                if skill_entry:
                    skill_records.append(skill_entry)

            # Also extract from qualifications if present
            qualifications = worker.get("qualifications", [])
            if isinstance(qualifications, list):
                for qual in qualifications:
                    skill_entry = self._map_workday_qualification(qual, worker_id)
                    if skill_entry:
                        skill_records.append(skill_entry)

        logger.info(
            "Extracted %d skill records from %d Workday workers",
            len(skill_records),
            len(workers),
        )
        return skill_records

    def _map_workday_skill(
        self, raw: dict[str, Any], worker_id: str
    ) -> dict[str, Any] | None:
        """Map a single Workday skill/competency to structured format."""
        if not isinstance(raw, dict):
            return None

        name = (
            raw.get("name")
            or raw.get("skillName")
            or raw.get("competencyName")
            or raw.get("descriptor")
            or ""
        )
        if not name:
            return None

        skill_id = raw.get("id") or raw.get("skillId") or name.lower().replace(" ", "_")

        # Map proficiency level
        raw_level = str(
            raw.get("proficiency")
            or raw.get("proficiencyLevel")
            or raw.get("level")
            or ""
        ).lower().strip()
        proficiency_level = self._PROFICIENCY_MAP.get(raw_level, 2)
        # Also support numeric levels directly
        if raw_level.isdigit():
            proficiency_level = max(1, min(5, int(raw_level)))

        # Infer category from skill group or type
        group = str(
            raw.get("skillGroup")
            or raw.get("category")
            or raw.get("type")
            or ""
        ).lower().strip()
        category = self._SKILL_GROUP_CATEGORY_MAP.get(group, "technical")

        years_exp = raw.get("yearsOfExperience") or raw.get("years_experience")

        return {
            "worker_id": worker_id,
            "skill_id": skill_id,
            "name": name,
            "category": category,
            "proficiency_level": proficiency_level,
            "framework": "custom",
            "framework_code": raw.get("frameworkCode") or raw.get("externalCode"),
            "years_experience": float(years_exp) if years_exp is not None else None,
            "source": "hr_system",
            "verified": bool(raw.get("verified") or raw.get("managerVerified")),
            "last_assessed_at": raw.get("lastAssessedDate") or raw.get("lastUpdated"),
            "raw_proficiency": raw_level or None,
        }

    def _map_workday_qualification(
        self, qual: dict[str, Any], worker_id: str
    ) -> dict[str, Any] | None:
        """Map a Workday qualification (certification, education) to a skill."""
        if not isinstance(qual, dict):
            return None
        name = qual.get("name") or qual.get("qualificationName") or ""
        if not name:
            return None

        qual_type = str(qual.get("type") or qual.get("qualificationType") or "").lower()
        category = "certification" if "cert" in qual_type else "domain"

        return {
            "worker_id": worker_id,
            "skill_id": name.lower().replace(" ", "_"),
            "name": name,
            "category": category,
            "proficiency_level": 3,
            "framework": "custom",
            "framework_code": qual.get("externalCode"),
            "years_experience": None,
            "source": "hr_system",
            "verified": True,
            "last_assessed_at": qual.get("issuedDate") or qual.get("completionDate"),
        }

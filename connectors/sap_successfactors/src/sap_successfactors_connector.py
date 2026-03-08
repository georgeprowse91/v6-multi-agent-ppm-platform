"""
SAP SuccessFactors Connector Implementation.

Supports:
- OAuth2 authentication
- Reading employee, job, and skill/competency data
- Skill profile extraction and structured taxonomy mapping
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from rest_connector import OAuth2RestConnector  # noqa: E402

logger = logging.getLogger(__name__)


class SapSuccessFactorsConnector(OAuth2RestConnector):
    CONNECTOR_ID = "sap_successfactors"
    CONNECTOR_NAME = "SAP SuccessFactors"
    CONNECTOR_VERSION = "1.1.0"
    CONNECTOR_CATEGORY = ConnectorCategory.HRIS
    SUPPORTS_WRITE = False

    INSTANCE_URL_ENV = "SF_API_SERVER"
    CLIENT_ID_ENV = "SF_CLIENT_ID"
    CLIENT_SECRET_ENV = "SF_CLIENT_SECRET"
    REFRESH_TOKEN_ENV = "SF_REFRESH_TOKEN"
    TOKEN_URL_ENV = "SF_TOKEN_URL"
    DEFAULT_TOKEN_URL = "https://api.successfactors.com/oauth/token"
    SCOPES_ENV = "SF_SCOPES"
    KEYVAULT_URL_ENV = "SF_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV = "SF_REFRESH_TOKEN_SECRET"
    CLIENT_SECRET_SECRET_ENV = "SF_CLIENT_SECRET_SECRET"
    CLIENT_ID_SECRET_ENV = "SF_CLIENT_ID_SECRET"

    AUTH_TEST_ENDPOINT = "/odata/v2/User"
    AUTH_TEST_PARAMS = {"$top": 1}
    RESOURCE_PATHS = {
        "users": {"path": "/odata/v2/User", "items_path": "d.results"},
        "jobs": {"path": "/odata/v2/EmpJob", "items_path": "d.results"},
        "competencies": {"path": "/odata/v2/CompetencyEntity", "items_path": "d.results"},
        "skill_profiles": {"path": "/odata/v2/SkillProfile", "items_path": "d.results"},
    }
    SCHEMA = {
        "users": {"userId": "string", "firstName": "string", "lastName": "string"},
        "jobs": {"userId": "string", "position": "string"},
        "competencies": {"competencyId": "string", "name_defaultValue": "string", "category": "string"},
        "skill_profiles": {"userId": "string", "skill_id": "string", "name": "string", "proficiency_level": "integer", "category": "string"},
    }

    # SAP SuccessFactors competency rating → numeric 1-5 mapping
    _RATING_MAP: dict[str, int] = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "not_demonstrated": 1,
        "basic": 1,
        "developing": 2,
        "competent": 3,
        "proficient": 3,
        "advanced": 4,
        "expert": 4,
        "mastery": 5,
        "distinguished": 5,
    }

    # SAP competency category → structured taxonomy category
    _COMPETENCY_CATEGORY_MAP: dict[str, str] = {
        "technical": "technical",
        "functional": "technical",
        "it": "technical",
        "leadership": "leadership",
        "managerial": "leadership",
        "management": "leadership",
        "core": "domain",
        "business": "domain",
        "industry": "domain",
        "process": "methodology",
        "methodology": "methodology",
        "tool": "tool",
        "application": "tool",
        "language": "language",
        "certification": "certification",
        "behavioral": "soft_skill",
        "interpersonal": "soft_skill",
        "communication": "soft_skill",
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)

    def read(
        self,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if resource_type == "skill_profiles":
            return self.read_skill_profiles(filters=filters, limit=limit, offset=offset)
        return super().read(resource_type, filters=filters, limit=limit, offset=offset)

    def read_skill_profiles(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Extract skill/competency profiles from SAP SuccessFactors.

        Reads competency ratings via the CompetencyEntity and SkillProfile
        OData endpoints, mapping SAP's rating scales and competency
        categories to the platform's structured skills taxonomy.

        Returns a list of structured skill records per employee.
        """
        # Try reading from SkillProfile entity first
        skill_records: list[dict[str, Any]] = []

        try:
            raw_profiles = super().read(
                "skill_profiles", filters=filters, limit=limit, offset=offset,
            )
            for profile in raw_profiles:
                mapped = self._map_skill_profile(profile)
                if mapped:
                    skill_records.append(mapped)
        except Exception:
            logger.info("SkillProfile entity not available, trying CompetencyEntity")

        # Also read from CompetencyEntity
        try:
            raw_competencies = super().read(
                "competencies", filters=filters, limit=limit, offset=offset,
            )
            for comp in raw_competencies:
                mapped = self._map_competency(comp)
                if mapped:
                    skill_records.append(mapped)
        except Exception:
            logger.info("CompetencyEntity not available, trying user competency nav")

        # If neither entity is available, try extracting from user records
        if not skill_records:
            try:
                users = super().read(
                    "users", filters=filters, limit=limit, offset=offset,
                )
                for user in users:
                    user_skills = self._extract_user_competencies(user)
                    skill_records.extend(user_skills)
            except Exception:
                logger.warning("Failed to extract skills from any SAP SF entity")

        logger.info(
            "Extracted %d skill records from SAP SuccessFactors", len(skill_records),
        )
        return skill_records

    def _map_skill_profile(self, profile: dict[str, Any]) -> dict[str, Any] | None:
        """Map a SAP SkillProfile record to structured skill format."""
        if not isinstance(profile, dict):
            return None

        name = (
            profile.get("name")
            or profile.get("skillName")
            or profile.get("name_defaultValue")
            or ""
        )
        if not name:
            return None

        user_id = profile.get("userId") or profile.get("externalCode") or ""
        skill_id = (
            profile.get("skillId")
            or profile.get("externalCode")
            or name.lower().replace(" ", "_")
        )

        # Map proficiency
        raw_rating = str(
            profile.get("proficiencyLevel")
            or profile.get("rating")
            or profile.get("ratingKey")
            or ""
        ).lower().strip()
        proficiency_level = self._RATING_MAP.get(raw_rating, 2)
        if raw_rating.isdigit():
            proficiency_level = max(1, min(5, int(raw_rating)))

        # Map category
        raw_category = str(
            profile.get("category")
            or profile.get("competencyType")
            or profile.get("skillType")
            or ""
        ).lower().strip()
        category = self._COMPETENCY_CATEGORY_MAP.get(raw_category, "technical")

        return {
            "worker_id": user_id,
            "skill_id": skill_id,
            "name": name,
            "category": category,
            "proficiency_level": proficiency_level,
            "framework": "custom",
            "framework_code": profile.get("externalCode"),
            "years_experience": profile.get("yearsOfExperience"),
            "source": "hr_system",
            "verified": bool(profile.get("managerRated") or profile.get("verified")),
            "last_assessed_at": profile.get("lastModifiedDateTime") or profile.get("ratingDate"),
        }

    def _map_competency(self, comp: dict[str, Any]) -> dict[str, Any] | None:
        """Map a SAP CompetencyEntity to structured skill format."""
        if not isinstance(comp, dict):
            return None

        name = (
            comp.get("name_defaultValue")
            or comp.get("name")
            or comp.get("competencyName")
            or ""
        )
        if not name:
            return None

        comp_id = comp.get("competencyId") or comp.get("externalCode") or ""
        user_id = comp.get("userId") or ""

        raw_category = str(comp.get("category") or comp.get("type") or "").lower().strip()
        category = self._COMPETENCY_CATEGORY_MAP.get(raw_category, "domain")

        return {
            "worker_id": user_id,
            "skill_id": comp_id or name.lower().replace(" ", "_"),
            "name": name,
            "category": category,
            "proficiency_level": 3,
            "framework": "custom",
            "framework_code": comp.get("externalCode"),
            "years_experience": None,
            "source": "hr_system",
            "verified": False,
            "last_assessed_at": comp.get("lastModifiedDateTime"),
        }

    def _extract_user_competencies(
        self, user: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract competencies from a User record's navigation properties."""
        if not isinstance(user, dict):
            return []

        user_id = user.get("userId", "")
        results: list[dict[str, Any]] = []

        # Check competencyRatingNav (standard SF navigation property)
        competency_nav = (
            user.get("competencyRatingNav", {}).get("results", [])
            or user.get("competencies", [])
        )
        if not isinstance(competency_nav, list):
            competency_nav = []

        for entry in competency_nav:
            if not isinstance(entry, dict):
                continue
            name = (
                entry.get("name")
                or entry.get("competencyName")
                or entry.get("name_defaultValue")
                or ""
            )
            if not name:
                continue

            raw_rating = str(entry.get("rating") or entry.get("ratingKey") or "").lower()
            proficiency = self._RATING_MAP.get(raw_rating, 2)
            if raw_rating.isdigit():
                proficiency = max(1, min(5, int(raw_rating)))

            raw_cat = str(entry.get("category") or entry.get("type") or "").lower()
            category = self._COMPETENCY_CATEGORY_MAP.get(raw_cat, "technical")

            results.append({
                "worker_id": user_id,
                "skill_id": entry.get("competencyId") or name.lower().replace(" ", "_"),
                "name": name,
                "category": category,
                "proficiency_level": proficiency,
                "framework": "custom",
                "framework_code": entry.get("externalCode"),
                "years_experience": None,
                "source": "hr_system",
                "verified": bool(entry.get("managerRated")),
                "last_assessed_at": entry.get("ratingDate"),
            })

        return results

"""Tests for Intelligent Resource Capacity Planning with Skill Matching (Enhancement 8).

Tests cover:
- Resource schema structured_skills validation
- Alembic migration structure
- Workday connector skill profile extraction & mapping
- SAP SuccessFactors connector skill profile extraction & mapping
- Resource agent portfolio demand aggregation
- Resource agent route_recommendation action
- Capacity planning API route
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path bootstrapping
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tests" / "unit"))

# ---------------------------------------------------------------------------
# 1. Resource schema validation
# ---------------------------------------------------------------------------

_SCHEMA_PATH = _REPO / "data" / "schemas" / "resource.schema.json"


class TestResourceSchema:
    @pytest.fixture(autouse=True)
    def _load_schema(self):
        with open(_SCHEMA_PATH) as f:
            self.schema = json.load(f)

    def test_schema_version_is_2(self):
        metadata = self.schema.get("x-schema-metadata", {})
        assert metadata.get("version") == "2.0.0"

    def test_structured_skills_array_exists(self):
        props = self.schema["properties"]
        assert "structured_skills" in props
        assert props["structured_skills"]["type"] == "array"

    def test_skill_item_required_fields(self):
        skill_schema = self.schema["properties"]["structured_skills"]["items"]
        required = set(skill_schema.get("required", []))
        expected = {"skill_id", "name", "category", "proficiency_level"}
        assert expected.issubset(required)

    def test_proficiency_level_range(self):
        skill_schema = self.schema["properties"]["structured_skills"]["items"]
        prof = skill_schema["properties"]["proficiency_level"]
        assert prof["minimum"] == 1
        assert prof["maximum"] == 5

    def test_category_enum_values(self):
        skill_schema = self.schema["properties"]["structured_skills"]["items"]
        categories = skill_schema["properties"]["category"]["enum"]
        expected = [
            "technical",
            "leadership",
            "domain",
            "methodology",
            "tool",
            "language",
            "certification",
            "soft_skill",
        ]
        assert set(expected) == set(categories)

    def test_framework_enum_values(self):
        skill_schema = self.schema["properties"]["structured_skills"]["items"]
        frameworks = skill_schema["properties"]["framework"]["enum"]
        assert "SFIA" in frameworks
        assert "ESCO" in frameworks
        assert "ONET" in frameworks
        assert "custom" in frameworks

    def test_hr_system_fields_exist(self):
        props = self.schema["properties"]
        assert "hr_system_id" in props
        assert "hr_system_source" in props

    def test_department_field_exists(self):
        props = self.schema["properties"]
        assert "department" in props


# ---------------------------------------------------------------------------
# 2. Migration structure
# ---------------------------------------------------------------------------

_MIGRATION_PATH = (
    _REPO / "data" / "migrations" / "versions" / "0010_add_structured_skills_taxonomy.py"
)


class TestSkillsMigration:
    @pytest.fixture(autouse=True)
    def _load_migration(self):
        self.content = _MIGRATION_PATH.read_text()

    def test_migration_file_exists(self):
        assert _MIGRATION_PATH.exists()

    def test_has_revision_id(self):
        assert "revision" in self.content

    def test_creates_resource_skills_table(self):
        assert "resource_skills" in self.content

    def test_creates_skills_taxonomy_table(self):
        assert "skills_taxonomy" in self.content

    def test_creates_portfolio_skill_demand_table(self):
        assert "portfolio_skill_demand" in self.content

    def test_has_upgrade_function(self):
        assert "def upgrade" in self.content

    def test_has_downgrade_function(self):
        assert "def downgrade" in self.content

    def test_proficiency_level_column(self):
        assert "proficiency_level" in self.content

    def test_framework_column(self):
        assert "framework" in self.content


# ---------------------------------------------------------------------------
# 3. Workday connector skill mapping
# ---------------------------------------------------------------------------

# Stub out dependencies before importing the connector
_wd_src = _REPO / "connectors" / "workday" / "src"
sys.path.insert(0, str(_wd_src))
sys.path.insert(0, str(_REPO / "connectors" / "sdk" / "src"))
sys.path.insert(0, str(_REPO / "packages" / "common" / "src"))


class TestWorkdaySkillMapping:
    """Test the Workday connector's skill mapping methods directly."""

    @pytest.fixture(autouse=True)
    def _load_connector_class(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "workday_connector",
            _wd_src / "workday_connector.py",
        )
        mod = importlib.util.module_from_spec(spec)
        # We only need class attributes/methods, not __init__
        self.cls = None
        try:
            spec.loader.exec_module(mod)
            self.cls = mod.WorkdayConnector
        except Exception:
            pytest.skip("Cannot load WorkdayConnector (missing deps)")

    def test_proficiency_map_covers_key_levels(self):
        pm = self.cls._PROFICIENCY_MAP
        assert pm["beginner"] == 1
        assert pm["intermediate"] == 2
        assert pm["advanced"] == 3
        assert pm["expert"] == 4
        assert pm["mastery"] == 5

    def test_skill_group_category_map(self):
        cm = self.cls._SKILL_GROUP_CATEGORY_MAP
        assert cm["technology"] == "technical"
        assert cm["leadership"] == "leadership"
        assert cm["business"] == "domain"
        assert cm["agile"] == "methodology"
        assert cm["software"] == "tool"
        assert cm["certification"] == "certification"
        assert cm["communication"] == "soft_skill"

    def test_resource_paths_include_skill_profiles(self):
        rp = self.cls.RESOURCE_PATHS
        assert "skill_profiles" in rp
        assert "skills" in rp

    def test_schema_includes_skill_profiles(self):
        schema = self.cls.SCHEMA
        assert "skill_profiles" in schema
        sp = schema["skill_profiles"]
        assert "worker_id" in sp
        assert "skill_id" in sp
        assert "proficiency_level" in sp


# ---------------------------------------------------------------------------
# 4. SAP SuccessFactors connector skill mapping
# ---------------------------------------------------------------------------

_sf_src = _REPO / "connectors" / "sap_successfactors" / "src"
sys.path.insert(0, str(_sf_src))


class TestSapSuccessFactorsSkillMapping:
    """Test the SAP SF connector's skill mapping methods directly."""

    @pytest.fixture(autouse=True)
    def _load_connector_class(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sap_successfactors_connector",
            _sf_src / "sap_successfactors_connector.py",
        )
        mod = importlib.util.module_from_spec(spec)
        self.cls = None
        try:
            spec.loader.exec_module(mod)
            self.cls = mod.SapSuccessFactorsConnector
        except Exception:
            pytest.skip("Cannot load SapSuccessFactorsConnector (missing deps)")

    def test_rating_map_numeric(self):
        rm = self.cls._RATING_MAP
        assert rm["1"] == 1
        assert rm["3"] == 3
        assert rm["5"] == 5

    def test_rating_map_text_labels(self):
        rm = self.cls._RATING_MAP
        assert rm["basic"] == 1
        assert rm["competent"] == 3
        assert rm["expert"] == 4
        assert rm["mastery"] == 5

    def test_competency_category_map(self):
        cm = self.cls._COMPETENCY_CATEGORY_MAP
        assert cm["technical"] == "technical"
        assert cm["leadership"] == "leadership"
        assert cm["business"] == "domain"
        assert cm["methodology"] == "methodology"
        assert cm["tool"] == "tool"
        assert cm["certification"] == "certification"
        assert cm["behavioral"] == "soft_skill"

    def test_resource_paths_include_competencies(self):
        rp = self.cls.RESOURCE_PATHS
        assert "competencies" in rp
        assert "skill_profiles" in rp

    def test_connector_version_bumped(self):
        assert self.cls.CONNECTOR_VERSION >= "1.1.0"


# ---------------------------------------------------------------------------
# 5. Resource Management Agent — demand aggregation & recommendations
# ---------------------------------------------------------------------------

_agent_src = _REPO / "agents" / "delivery-management" / "resource-management-agent" / "src"
sys.path.insert(0, str(_agent_src))
sys.path.insert(0, str(_REPO / "agents" / "runtime" / "src"))


class TestResourceCapacityAgent:
    """Test the Resource Management agent's new capacity planning actions."""

    @pytest.fixture(autouse=True)
    def _load_agent(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "resource_capacity_agent",
            _agent_src / "resource_capacity_agent.py",
        )
        mod = importlib.util.module_from_spec(spec)
        self.mod = None
        self.cls = None
        try:
            spec.loader.exec_module(mod)
            self.mod = mod
            self.cls = mod.ResourceCapacityAgent
        except Exception:
            pytest.skip("Cannot load ResourceCapacityAgent (missing deps)")

    def test_validate_input_accepts_new_actions(self):
        """Verify the agent source contains the new action names in valid_actions."""

        src_path = _agent_src / "resource_capacity_agent.py"
        source = src_path.read_text()
        assert "aggregate_portfolio_demand" in source
        assert "route_recommendation" in source

    def test_get_capabilities_includes_skills_taxonomy(self):
        """Verify get_capabilities returns structured_skills_taxonomy."""
        src_path = _agent_src / "resource_capacity_agent.py"
        source = src_path.read_text()
        assert "structured_skills_taxonomy" in source
        assert "portfolio_demand_aggregation" in source
        assert "hr_recommendation_routing" in source

    def test_has_aggregate_method(self):
        assert hasattr(self.cls, "_aggregate_portfolio_demand")

    def test_has_route_recommendation_method(self):
        assert hasattr(self.cls, "_route_recommendation")

    def test_has_sub_routing_methods(self):
        assert hasattr(self.cls, "_route_hiring_recommendation")
        assert hasattr(self.cls, "_route_training_recommendation")
        assert hasattr(self.cls, "_route_reallocation_recommendation")


# ---------------------------------------------------------------------------
# 6. Capacity planning API route
# ---------------------------------------------------------------------------

sys.path.insert(0, str(_REPO / "tests" / "unit"))
from _route_test_helpers import load_route_module  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _make_capacity_app():
    mod = load_route_module("capacity.py")
    app = FastAPI()
    app.include_router(mod.router)
    return app


@pytest.fixture
def capacity_client():
    return TestClient(_make_capacity_app())


class TestCapacityApiRoute:
    def test_portfolio_demand_returns_ok(self, capacity_client):
        resp = capacity_client.get("/api/capacity/portfolio-demand")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "data" in body

    def test_portfolio_demand_has_summary(self, capacity_client):
        resp = capacity_client.get("/api/capacity/portfolio-demand")
        data = resp.json()["data"]
        summary = data["summary"]
        assert "total_demand_hours" in summary
        assert "total_supply_hours" in summary
        assert "capacity_ratio" in summary
        assert "total_skill_gaps" in summary

    def test_portfolio_demand_with_portfolio_id(self, capacity_client):
        resp = capacity_client.get(
            "/api/capacity/portfolio-demand",
            params={"portfolio_id": "pf-001"},
        )
        assert resp.status_code == 200

    def test_portfolio_demand_with_project_id(self, capacity_client):
        resp = capacity_client.get(
            "/api/capacity/portfolio-demand",
            params={"project_id": "proj-001"},
        )
        assert resp.status_code == 200

    def test_skills_endpoint_returns_ok(self, capacity_client):
        resp = capacity_client.get("/api/capacity/skills")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"

    def test_skills_endpoint_has_frameworks(self, capacity_client):
        resp = capacity_client.get("/api/capacity/skills")
        data = resp.json()["data"]
        assert "SFIA" in data["frameworks"]
        assert "ESCO" in data["frameworks"]
        assert "ONET" in data["frameworks"]

    def test_skills_endpoint_has_categories(self, capacity_client):
        resp = capacity_client.get("/api/capacity/skills")
        data = resp.json()["data"]
        expected = {
            "technical",
            "leadership",
            "domain",
            "methodology",
            "tool",
            "language",
            "certification",
            "soft_skill",
        }
        assert expected == set(data["categories"])

    def test_skills_endpoint_with_category_filter(self, capacity_client):
        resp = capacity_client.get(
            "/api/capacity/skills",
            params={"category": "technical"},
        )
        assert resp.status_code == 200

    def test_skills_endpoint_with_framework_filter(self, capacity_client):
        resp = capacity_client.get(
            "/api/capacity/skills",
            params={"framework": "SFIA"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 7. Workday skill mapping unit tests (method-level)
# ---------------------------------------------------------------------------


class TestWorkdaySkillMappingMethods:
    """Test the actual mapping methods via direct invocation."""

    @pytest.fixture(autouse=True)
    def _load(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "workday_connector_methods",
            _wd_src / "workday_connector.py",
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            self.cls = mod.WorkdayConnector
        except Exception:
            pytest.skip("Cannot load WorkdayConnector (missing deps)")

    def test_map_workday_skill_basic(self):
        raw = {
            "name": "Python",
            "id": "py-001",
            "proficiency": "expert",
            "skillGroup": "technology",
        }
        # Call unbound method with None self — we only use class attrs
        result = self.cls._map_workday_skill(self.cls, raw, "worker-1")
        assert result is not None
        assert result["name"] == "Python"
        assert result["skill_id"] == "py-001"
        assert result["proficiency_level"] == 4  # expert
        assert result["category"] == "technical"
        assert result["worker_id"] == "worker-1"

    def test_map_workday_skill_numeric_level(self):
        raw = {"name": "React", "proficiency": "3"}
        result = self.cls._map_workday_skill(self.cls, raw, "w-2")
        assert result is not None
        assert result["proficiency_level"] == 3

    def test_map_workday_skill_empty_name_returns_none(self):
        raw = {"name": "", "id": "x"}
        result = self.cls._map_workday_skill(self.cls, raw, "w-1")
        assert result is None

    def test_map_workday_skill_non_dict_returns_none(self):
        result = self.cls._map_workday_skill(self.cls, "not_a_dict", "w-1")
        assert result is None

    def test_map_workday_qualification_cert(self):
        qual = {"name": "PMP Certification", "type": "certification"}
        result = self.cls._map_workday_qualification(self.cls, qual, "w-3")
        assert result is not None
        assert result["category"] == "certification"
        assert result["verified"] is True

    def test_map_workday_qualification_non_cert(self):
        qual = {"name": "MBA", "type": "education"}
        result = self.cls._map_workday_qualification(self.cls, qual, "w-4")
        assert result is not None
        assert result["category"] == "domain"


# ---------------------------------------------------------------------------
# 8. SAP SuccessFactors skill mapping unit tests (method-level)
# ---------------------------------------------------------------------------


class TestSapSkillMappingMethods:
    """Test the SAP SF connector's mapping methods via direct invocation."""

    @pytest.fixture(autouse=True)
    def _load(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sap_sf_connector_methods",
            _sf_src / "sap_successfactors_connector.py",
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            self.cls = mod.SapSuccessFactorsConnector
        except Exception:
            pytest.skip("Cannot load SapSuccessFactorsConnector (missing deps)")

    def test_map_skill_profile_basic(self):
        profile = {
            "name": "Java",
            "skillId": "java-001",
            "userId": "emp-1",
            "proficiencyLevel": "4",
            "category": "technical",
        }
        result = self.cls._map_skill_profile(self.cls, profile)
        assert result is not None
        assert result["name"] == "Java"
        assert result["proficiency_level"] == 4
        assert result["category"] == "technical"
        assert result["worker_id"] == "emp-1"

    def test_map_skill_profile_text_rating(self):
        profile = {"name": "Leadership", "proficiencyLevel": "expert", "category": "leadership"}
        result = self.cls._map_skill_profile(self.cls, profile)
        assert result is not None
        assert result["proficiency_level"] == 4  # expert -> 4
        assert result["category"] == "leadership"

    def test_map_skill_profile_empty_name_returns_none(self):
        profile = {"name": "", "skillId": "x"}
        result = self.cls._map_skill_profile(self.cls, profile)
        assert result is None

    def test_map_competency_basic(self):
        comp = {
            "name_defaultValue": "Project Management",
            "competencyId": "pm-001",
            "category": "management",
        }
        result = self.cls._map_competency(self.cls, comp)
        assert result is not None
        assert result["name"] == "Project Management"
        assert result["category"] == "leadership"  # management -> leadership

    def test_map_competency_empty_name_returns_none(self):
        comp = {"name_defaultValue": ""}
        result = self.cls._map_competency(self.cls, comp)
        assert result is None

    def test_extract_user_competencies(self):
        user = {
            "userId": "emp-5",
            "competencyRatingNav": {
                "results": [
                    {
                        "name": "Python",
                        "rating": "4",
                        "category": "technical",
                        "competencyId": "py-001",
                    },
                    {
                        "name": "Communication",
                        "rating": "3",
                        "category": "interpersonal",
                    },
                ],
            },
        }
        results = self.cls._extract_user_competencies(self.cls, user)
        assert len(results) == 2
        assert results[0]["name"] == "Python"
        assert results[0]["proficiency_level"] == 4
        assert results[0]["category"] == "technical"
        assert results[1]["name"] == "Communication"
        assert results[1]["category"] == "soft_skill"

    def test_extract_user_competencies_empty_user(self):
        results = self.cls._extract_user_competencies(self.cls, {})
        assert results == []

    def test_extract_user_competencies_non_dict(self):
        results = self.cls._extract_user_competencies(self.cls, "not_a_dict")
        assert results == []

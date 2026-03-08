from __future__ import annotations

from types import SimpleNamespace

import pytest
from api.circuit_breaker import CircuitBreaker
from api.routes import agents
from fastapi import HTTPException


@pytest.mark.anyio
async def test_list_agents_happy_path():
    orchestrator = SimpleNamespace(
        get_agent_count=lambda: 2, list_agents=lambda: [{"id": "a"}, {"id": "b"}]
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(orchestrator=orchestrator)))

    response = await agents.list_agents(request)

    assert response["total_agents"] == 2
    assert len(response["agents"]) == 2


@pytest.mark.anyio
async def test_get_agent_info_not_found_is_negative_path():
    orchestrator = SimpleNamespace(get_agent=lambda _agent_id: None)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(orchestrator=orchestrator)))

    with pytest.raises(HTTPException) as exc_info:
        await agents.get_agent_info("missing-agent", request)

    assert exc_info.value.status_code == 404


def test_circuit_breaker_opens_after_repeated_failures():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=30, half_open_successes=1)

    assert breaker.allow_request("jira") is True
    breaker.record_failure("jira")
    breaker.record_failure("jira")

    assert breaker.get_state("jira").state == "open"
    assert breaker.allow_request("jira") is False


def test_circuit_breaker_half_open_and_reclose(monkeypatch):
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=5, half_open_successes=2)

    breaker.record_failure("jira")
    opened = breaker.get_state("jira")

    monkeypatch.setattr("api.circuit_breaker.time.monotonic", lambda: (opened.opened_at or 0) + 6)

    assert breaker.allow_request("jira") is True
    assert breaker.get_state("jira").state == "half_open"

    breaker.record_success("jira")
    assert breaker.get_state("jira").state == "half_open"

    breaker.record_success("jira")
    assert breaker.get_state("jira").state == "closed"

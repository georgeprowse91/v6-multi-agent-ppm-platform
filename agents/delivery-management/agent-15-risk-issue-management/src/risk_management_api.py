"""FastAPI endpoints for the Risk Management Agent."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from risk_management_agent import RiskManagementAgent

app = FastAPI(title="Risk Management Agent API", version="0.1.0")
_agent: RiskManagementAgent | None = None


async def get_agent() -> RiskManagementAgent:
    global _agent
    if _agent is None:
        _agent = RiskManagementAgent()
        await _agent.initialize()
    return _agent


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/risks")
async def list_risks(
    project_id: str | None = Query(default=None),
    portfolio_id: str | None = Query(default=None),
) -> dict[str, Any]:
    agent = await get_agent()
    risks = list(agent.risk_register.values())
    if agent.db_service:
        try:
            risks = await agent.db_service.query(
                "risks",
                filters={"project_id": project_id, "portfolio_id": portfolio_id},
                limit=500,
            )
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            risks = list(agent.risk_register.values())
    if project_id:
        risks = [risk for risk in risks if risk.get("project_id") == project_id]
    if portfolio_id:
        risks = [risk for risk in risks if risk.get("portfolio_id") == portfolio_id]
    return {"count": len(risks), "risks": risks}


@app.get("/risks/{risk_id}")
async def get_risk(risk_id: str) -> dict[str, Any]:
    agent = await get_agent()
    risk = agent.risk_register.get(risk_id)
    if agent.db_service:
        try:
            risk = await agent.db_service.retrieve("risks", risk_id) or risk
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            risk = risk
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    return risk


@app.get("/risks/{risk_id}/mitigation")
async def get_mitigation_plan(risk_id: str) -> dict[str, Any]:
    agent = await get_agent()
    risk = agent.risk_register.get(risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    plan_id = risk.get("mitigation_plan_id")
    if not plan_id:
        raise HTTPException(status_code=404, detail="Mitigation plan not found")
    plan = agent.mitigation_plans.get(plan_id)
    if agent.db_service:
        try:
            plan = await agent.db_service.retrieve("mitigation_plans", plan_id) or plan
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            plan = plan
    if not plan:
        raise HTTPException(status_code=404, detail="Mitigation plan not found")
    return plan


@app.get("/risks/{risk_id}/events")
async def get_risk_events(risk_id: str) -> dict[str, Any]:
    agent = await get_agent()
    events = [
        event
        for event in agent.risk_events
        if event.get("payload", {}).get("risk_id") == risk_id
    ]
    return {"risk_id": risk_id, "events": events}


@app.get("/risks/{risk_id}/assessments")
async def get_risk_assessments(risk_id: str) -> dict[str, Any]:
    agent = await get_agent()
    assessments = []
    if agent.db_service:
        try:
            assessments = await agent.db_service.query(
                "risk_assessments",
                filters={"risk_id": risk_id},
                limit=100,
            )
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            assessments = []
    return {"risk_id": risk_id, "assessments": assessments}


@app.get("/risks/{risk_id}/impacts")
async def get_risk_impacts(risk_id: str) -> dict[str, Any]:
    agent = await get_agent()
    impacts = []
    if agent.db_service:
        try:
            impacts = await agent.db_service.query(
                "risk_impacts",
                filters={"risk_id": risk_id},
                limit=100,
            )
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            impacts = []
    return {"risk_id": risk_id, "impacts": impacts}


@app.get("/risks/{risk_id}/simulations")
async def get_risk_simulations(risk_id: str) -> dict[str, Any]:
    agent = await get_agent()
    simulations = []
    project_id = None
    risk = agent.risk_register.get(risk_id)
    if risk:
        project_id = risk.get("project_id")
    if agent.db_service:
        try:
            simulations = await agent.db_service.query(
                "risk_simulations",
                filters={"project_id": project_id} if project_id else None,
                limit=100,
            )
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            simulations = []
    return {"risk_id": risk_id, "simulations": simulations}


@app.get("/risks/{risk_id}/triggers")
async def get_risk_triggers(risk_id: str) -> dict[str, Any]:
    agent = await get_agent()
    triggers = [
        trigger
        for trigger in agent.triggers.values()
        if trigger.get("risk_id") == risk_id
    ]
    if agent.db_service:
        try:
            triggers = await agent.db_service.query(
                "risk_trigger_definitions",
                filters={"risk_id": risk_id},
                limit=100,
            )
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            triggers = triggers
    return {"risk_id": risk_id, "triggers": triggers}

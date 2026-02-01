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
    if project_id:
        risks = [risk for risk in risks if risk.get("project_id") == project_id]
    if portfolio_id:
        risks = [risk for risk in risks if risk.get("portfolio_id") == portfolio_id]
    return {"count": len(risks), "risks": risks}


@app.get("/risks/{risk_id}")
async def get_risk(risk_id: str) -> dict[str, Any]:
    agent = await get_agent()
    risk = agent.risk_register.get(risk_id)
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

"""Enterprise routes: portfolio demand, prioritisation, capacity, scenarios,
finance, agile, comments, notifications, sync, alerts, packs, boards, automations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from routes._deps import (
    ALERTS_STORE_PATH,
    CAPACITY_STORE_PATH,
    COMMENTS_STORE_PATH,
    DEMAND_STORE_PATH,
    NOTIFICATIONS_STORE_PATH,
    PACKS_STORE_PATH,
    PRIORITISATION_STORE_PATH,
    SCENARIOS_STORE_PATH,
    STORAGE_DIR,
    SYNC_STORE_PATH,
    _approval_payload,
    _audit_record,
    _demo_mode_enabled,
    _ensure_notifications,
    _load_store,
    _require_session,
    _write_json,
    demo_outbox,
    permission_required,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Portfolio Demand
# ---------------------------------------------------------------------------


@router.get("/api/portfolio/{portfolio_id}/demand")
@permission_required("portfolio.view")
async def list_portfolio_demand(portfolio_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(DEMAND_STORE_PATH, {"items": []})
    return {"items": [i for i in store.get("items", []) if i.get("portfolio_id") == portfolio_id]}


@router.post("/api/portfolio/{portfolio_id}/demand")
@permission_required("config.manage")
async def create_portfolio_demand(
    portfolio_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(DEMAND_STORE_PATH, {"items": []})
    demand_id = payload.get("id") or f"dem-{uuid4().hex[:10]}"
    row = {"id": demand_id, "portfolio_id": portfolio_id, **payload}
    row.setdefault("status", "intake")
    store.setdefault("items", []).append(row)
    _write_json(DEMAND_STORE_PATH, store)
    _audit_record(
        request,
        "portfolio.demand.create",
        {"resource": "demand", "portfolio_id": portfolio_id, "demand_id": demand_id},
    )
    return row


@router.patch("/api/portfolio/{portfolio_id}/demand/{demand_id}")
@permission_required("config.manage")
async def patch_portfolio_demand(
    portfolio_id: str, demand_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(DEMAND_STORE_PATH, {"items": []})
    for row in store.get("items", []):
        if row.get("portfolio_id") == portfolio_id and row.get("id") == demand_id:
            row.update(payload)
            _write_json(DEMAND_STORE_PATH, store)
            _audit_record(
                request,
                "portfolio.demand.update",
                {"resource": "demand", "portfolio_id": portfolio_id, "demand_id": demand_id},
            )
            return row
    raise HTTPException(status_code=404, detail="Demand not found")


# ---------------------------------------------------------------------------
# Prioritisation / Capacity / Scenarios
# ---------------------------------------------------------------------------


@router.post("/api/portfolio/{portfolio_id}/prioritisation/score")
@permission_required("portfolio.view")
async def score_prioritisation(portfolio_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    demand = _load_store(DEMAND_STORE_PATH, {"items": []}).get("items", [])
    model = _load_store(
        PRIORITISATION_STORE_PATH,
        {"weights": {"value": 0.5, "effort": 0.2, "risk": 0.3}, "runs": []},
    )
    weights = model.get("weights", {"value": 0.5, "effort": 0.2, "risk": 0.3})
    rows = []
    for item in demand:
        if item.get("portfolio_id") != portfolio_id:
            continue
        value = float(item.get("value", 5))
        effort = float(item.get("effort", 5))
        risk = float(item.get("risk", 5))
        score = round(
            value * weights.get("value", 0.5)
            + (10 - effort) * weights.get("effort", 0.2)
            + (10 - risk) * weights.get("risk", 0.3),
            3,
        )
        rows.append({**item, "score": score})
    rows.sort(key=lambda x: x["score"], reverse=True)
    run = {
        "id": f"run-{uuid4().hex[:8]}",
        "portfolio_id": portfolio_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": rows,
    }
    model.setdefault("runs", []).append(run)
    _write_json(PRIORITISATION_STORE_PATH, model)
    return run


@router.get("/api/portfolio/{portfolio_id}/capacity")
@permission_required("portfolio.view")
async def get_capacity(portfolio_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(CAPACITY_STORE_PATH, {"entries": []})
    return {
        "entries": [e for e in store.get("entries", []) if e.get("portfolio_id") == portfolio_id]
    }


@router.post("/api/portfolio/{portfolio_id}/capacity")
@permission_required("config.manage")
async def upsert_capacity(
    portfolio_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(CAPACITY_STORE_PATH, {"entries": []})
    entry = {
        "id": payload.get("id") or f"cap-{uuid4().hex[:8]}",
        "portfolio_id": portfolio_id,
        **payload,
    }
    entries = [e for e in store.get("entries", []) if e.get("id") != entry["id"]]
    entries.append(entry)
    store["entries"] = entries
    _write_json(CAPACITY_STORE_PATH, store)
    return entry


@router.post("/api/portfolio/{portfolio_id}/scenarios/run")
@permission_required("portfolio.view")
async def run_scenarios(
    portfolio_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    name = payload.get("name", "scenario")
    demand = _load_store(DEMAND_STORE_PATH, {"items": []}).get("items", [])
    selected = [d for d in demand if d.get("portfolio_id") == portfolio_id][
        : payload.get("limit", 10)
    ]
    score = round(
        sum(float(d.get("value", 5)) - float(d.get("effort", 5)) * 0.3 for d in selected), 3
    )
    budget = round(sum(float(d.get("cost", 100)) for d in selected), 2)
    record = {
        "id": payload.get("id") or f"scn-{uuid4().hex[:8]}",
        "portfolio_id": portfolio_id,
        "name": name,
        "value_score": score,
        "budget": budget,
        "selected_ids": [d.get("id") for d in selected],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "published": False,
    }
    store = _load_store(SCENARIOS_STORE_PATH, {"scenarios": [], "published_decisions": []})
    store.setdefault("scenarios", []).append(record)
    _write_json(SCENARIOS_STORE_PATH, store)
    return record


@router.get("/api/portfolio/{portfolio_id}/scenarios/compare")
@permission_required("portfolio.view")
async def compare_scenarios(portfolio_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(SCENARIOS_STORE_PATH, {"scenarios": []})
    rows = [s for s in store.get("scenarios", []) if s.get("portfolio_id") == portfolio_id]
    rows.sort(key=lambda s: s.get("value_score", 0), reverse=True)
    return {"scenarios": rows}


@router.post("/api/portfolio/{portfolio_id}/scenarios/{scenario_id}/publish")
@permission_required("intake.approve")
async def publish_scenario_decision(
    portfolio_id: str, scenario_id: str, request: Request
) -> dict[str, Any]:
    session = _require_session(request)
    store = _load_store(SCENARIOS_STORE_PATH, {"scenarios": [], "published_decisions": []})
    target = None
    for row in store.get("scenarios", []):
        if row.get("portfolio_id") == portfolio_id and row.get("id") == scenario_id:
            row["published"] = True
            target = row
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    decision = {
        "portfolio_id": portfolio_id,
        "scenario_id": scenario_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    store.setdefault("published_decisions", []).append(decision)
    _write_json(SCENARIOS_STORE_PATH, store)
    if _demo_mode_enabled():
        demo_outbox.push(
            "sor_publish",
            {
                "tenant_id": session.get("tenant_id") or "demo-tenant",
                "resource": "scenario_decision",
                **decision,
            },
        )
    _audit_record(
        request,
        "portfolio.scenario.publish",
        {"resource": "scenario", "portfolio_id": portfolio_id, "scenario_id": scenario_id},
    )
    return {"status": "published", "decision": decision}


# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------


@router.get("/api/finance/budgets")
@permission_required("portfolio.view")
async def list_finance_budgets(workspace_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(STORAGE_DIR / "finance_budget.json", {"budgets": []})
    return {
        "budgets": [b for b in store.get("budgets", []) if b.get("workspace_id") == workspace_id]
    }


@router.post("/api/finance/budgets")
@permission_required("config.manage")
async def create_finance_budget(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "finance_budget.json"
    store = _load_store(path, {"budgets": []})
    prior = [
        b for b in store.get("budgets", []) if b.get("workspace_id") == payload.get("workspace_id")
    ]
    version = len(prior) + 1
    row = {"id": f"bud-{uuid4().hex[:8]}", "version": version, **payload}
    if prior:
        row["diff"] = {
            k: row.get("amounts", {}).get(k, 0) - prior[-1].get("amounts", {}).get(k, 0)
            for k in set(row.get("amounts", {})) | set(prior[-1].get("amounts", {}))
        }
    else:
        row["diff"] = {}
    store.setdefault("budgets", []).append(row)
    _write_json(path, store)
    return row


@router.post("/api/finance/change-requests")
@permission_required("portfolio.view")
async def submit_change_request(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    session = _require_session(request)
    path = STORAGE_DIR / "finance_change_requests.json"
    store = _load_store(path, {"change_requests": []})
    row = {
        "id": f"cr-{uuid4().hex[:8]}",
        "status": "submitted",
        "submitted_by": session.get("subject", "user"),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    store.setdefault("change_requests", []).append(row)
    _write_json(path, store)
    return row


@router.post("/api/finance/change-requests/{request_id}/decision")
@permission_required("intake.approve")
async def decide_change_request(
    request_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "finance_change_requests.json"
    store = _load_store(path, {"change_requests": []})
    for row in store.get("change_requests", []):
        if row.get("id") == request_id:
            if payload.get("decision") not in {"approve", "reject"}:
                raise HTTPException(status_code=400, detail="decision must be approve|reject")
            row["status"] = "approved" if payload.get("decision") == "approve" else "rejected"
            row["decision_at"] = datetime.now(timezone.utc).isoformat()
            _write_json(path, store)
            return row
    raise HTTPException(status_code=404, detail="Change request not found")


@router.get("/api/finance/evidence/export")
@permission_required("audit.view")
async def export_finance_evidence(workspace_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    budgets = _load_store(STORAGE_DIR / "finance_budget.json", {"budgets": []}).get("budgets", [])
    changes = _load_store(
        STORAGE_DIR / "finance_change_requests.json", {"change_requests": []}
    ).get("change_requests", [])
    return {
        "workspace_id": workspace_id,
        "budgets": [b for b in budgets if b.get("workspace_id") == workspace_id],
        "change_requests": [c for c in changes if c.get("workspace_id") == workspace_id],
        "approvals": _approval_payload().get("approvals", []),
    }


# ---------------------------------------------------------------------------
# Agile
# ---------------------------------------------------------------------------


@router.get("/api/agile/backlog")
@permission_required("portfolio.view")
async def agile_backlog(program_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(STORAGE_DIR / "agile_backlog.json", {"items": []})
    return {"items": [i for i in store.get("items", []) if i.get("program_id") == program_id]}


@router.post("/api/agile/backlog")
@permission_required("config.manage")
async def agile_upsert_backlog(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "agile_backlog.json"
    store = _load_store(path, {"items": []})
    row = {"id": payload.get("id") or f"agl-{uuid4().hex[:8]}", **payload}
    store["items"] = [i for i in store.get("items", []) if i.get("id") != row["id"]]
    store["items"].append(row)
    _write_json(path, store)
    return row


@router.post("/api/agile/pi/create")
@permission_required("config.manage")
async def agile_create_pi(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "agile_pi.json"
    store = _load_store(path, {"pis": []})
    row = {
        "id": payload.get("id") or f"pi-{uuid4().hex[:8]}",
        "iterations": payload.get("iterations", []),
        "teams": payload.get("teams", []),
        **payload,
    }
    store.setdefault("pis", []).append(row)
    _write_json(path, store)
    return row


@router.get("/api/agile/predictability")
@permission_required("analytics.view")
async def agile_predictability(program_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    backlog = _load_store(STORAGE_DIR / "agile_backlog.json", {"items": []}).get("items", [])
    rows = [r for r in backlog if r.get("program_id") == program_id]
    planned = sum(float(r.get("planned_points", 0)) for r in rows) or 1
    achieved = sum(float(r.get("achieved_points", 0)) for r in rows)
    score = round(achieved / planned, 3)
    metrics = {
        "program_id": program_id,
        "planned": planned,
        "achieved": achieved,
        "predictability": score,
    }
    path = STORAGE_DIR / "agile_metrics.json"
    store = _load_store(path, {"history": []})
    store.setdefault("history", []).append(
        {**metrics, "at": datetime.now(timezone.utc).isoformat()}
    )
    _write_json(path, store)
    return metrics


# ---------------------------------------------------------------------------
# Comments / Notifications
# ---------------------------------------------------------------------------


@router.get("/api/comments")
@permission_required("portfolio.view")
async def list_comments(workspace_id: str, artifact_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(COMMENTS_STORE_PATH, {"comments": []})
    return {
        "comments": [
            c
            for c in store.get("comments", [])
            if c.get("workspace_id") == workspace_id and c.get("artifact_id") == artifact_id
        ]
    }


@router.post("/api/comments")
@permission_required("portfolio.view")
async def create_comment(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    session = _require_session(request)
    store = _load_store(COMMENTS_STORE_PATH, {"comments": []})
    comment = {
        "id": f"cmt-{uuid4().hex[:10]}",
        "author": session.get("subject", "user"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    store.setdefault("comments", []).append(comment)
    _write_json(COMMENTS_STORE_PATH, store)
    mentions = [part[1:] for part in str(payload.get("text", "")).split() if part.startswith("@")]
    if mentions:
        nstore = _load_store(NOTIFICATIONS_STORE_PATH, {"notifications": []})
        notifications = _ensure_notifications(nstore, session.get("tenant_id") or "demo-tenant")
        for m in mentions:
            notifications.append(
                {
                    "id": f"ntf-{uuid4().hex[:10]}",
                    "user_id": m,
                    "message": f"Mentioned in comment {comment['id']}",
                    "read": False,
                    "created_at": comment["created_at"],
                }
            )
        _write_json(NOTIFICATIONS_STORE_PATH, nstore)
    return comment


@router.get("/api/notifications")
@permission_required("portfolio.view")
async def list_notifications(request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(NOTIFICATIONS_STORE_PATH, {"notifications": []})
    return {"notifications": store.get("notifications", [])}


@router.post("/api/notifications/{notification_id}/read")
@permission_required("portfolio.view")
async def mark_notification_read(notification_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(NOTIFICATIONS_STORE_PATH, {"notifications": []})
    for n in store.get("notifications", []):
        if n.get("id") == notification_id:
            n["read"] = True
            _write_json(NOTIFICATIONS_STORE_PATH, store)
            return n
    raise HTTPException(status_code=404, detail="Notification not found")


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


@router.post("/api/sync/diff")
@permission_required("portfolio.view")
async def sync_diff(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    source = payload.get("source", [])
    target = payload.get("target", [])
    by_id = {item["id"]: item for item in target if isinstance(item, dict) and item.get("id")}
    diffs = []
    conflicts = []
    for item in source:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        t = by_id.get(item["id"])
        if not t:
            diffs.append({"id": item["id"], "type": "create", "incoming": item})
        elif t != item:
            conflicts.append(
                {"id": item["id"], "incoming": item, "current": t, "status": "requires_decision"}
            )
            diffs.append({"id": item["id"], "type": "update", "incoming": item, "current": t})
    store = _load_store(SYNC_STORE_PATH, {"conflicts": []})
    store["conflicts"] = conflicts
    _write_json(SYNC_STORE_PATH, store)
    return {"diffs": diffs, "conflicts": conflicts}


@router.get("/api/sync/conflicts")
@permission_required("portfolio.view")
async def get_sync_conflicts(request: Request) -> dict[str, Any]:
    _require_session(request)
    return _load_store(SYNC_STORE_PATH, {"conflicts": []})


@router.post("/api/sync/conflicts/{conflict_id}/resolve")
@permission_required("intake.approve")
async def resolve_sync_conflict(
    conflict_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(SYNC_STORE_PATH, {"conflicts": []})
    for c in store.get("conflicts", []):
        if c.get("id") == conflict_id:
            decision = payload.get("decision")
            if decision not in {"incoming", "current"}:
                raise HTTPException(status_code=400, detail="decision must be incoming|current")
            c["status"] = "resolved"
            c["resolution"] = decision
            _write_json(SYNC_STORE_PATH, store)
            return c
    raise HTTPException(status_code=404, detail="Conflict not found")


@router.post("/api/sync/publish")
@permission_required("intake.approve")
async def sync_publish(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    session = _require_session(request)
    if _demo_mode_enabled():
        demo_outbox.push(
            "sync_publish", {"tenant_id": session.get("tenant_id") or "demo-tenant", **payload}
        )
    _audit_record(
        request,
        "sync.publish",
        {"resource": "sync", "entity_type": payload.get("entity_type", "unknown")},
    )
    return {"status": "queued", "demo_mode": _demo_mode_enabled()}


# ---------------------------------------------------------------------------
# Alerts / Packs / Boards / Automations
# ---------------------------------------------------------------------------


@router.post("/api/alerts/compute")
@permission_required("analytics.view")
async def compute_alerts(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    seed = abs(hash(payload.get("workspace_id", "demo"))) % 100
    alerts = [
        {
            "id": "schedule-slip",
            "score": round((seed % 37) / 100 + 0.55, 3),
            "type": "schedule_slip_risk",
        },
        {
            "id": "budget-overrun",
            "score": round((seed % 29) / 100 + 0.5, 3),
            "type": "budget_overrun_risk",
        },
        {
            "id": "gate-readiness",
            "score": round((seed % 23) / 100 + 0.45, 3),
            "type": "gate_readiness_risk",
        },
    ]
    store = _load_store(ALERTS_STORE_PATH, {"history": []})
    store.setdefault("history", []).append(
        {
            "workspace_id": payload.get("workspace_id", "demo"),
            "alerts": alerts,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _write_json(ALERTS_STORE_PATH, store)
    return {"alerts": alerts}


@router.post("/api/packs/{pack_type}/generate")
@permission_required("analytics.view")
async def generate_pack(
    pack_type: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    if pack_type not in {"steering", "evidence", "comms"}:
        raise HTTPException(status_code=400, detail="Unsupported pack type")
    store = _load_store(PACKS_STORE_PATH, {"packs": []})
    artifact = {
        "id": f"pack-{uuid4().hex[:8]}",
        "pack_type": pack_type,
        "workspace_id": payload.get("workspace_id"),
        "title": f"{pack_type.title()} Pack",
        "content": payload.get("content", "Auto-generated pack"),
        "editable": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    store.setdefault("packs", []).append(artifact)
    _write_json(PACKS_STORE_PATH, store)
    return artifact


@router.post("/api/packs/{pack_id}/publish")
@permission_required("intake.approve")
async def publish_pack(pack_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    store = _load_store(PACKS_STORE_PATH, {"packs": []})
    for pack in store.get("packs", []):
        if pack.get("id") == pack_id:
            pack["published_at"] = datetime.now(timezone.utc).isoformat()
            _write_json(PACKS_STORE_PATH, store)
            if _demo_mode_enabled():
                demo_outbox.push(
                    "sor_publish",
                    {
                        "tenant_id": session.get("tenant_id") or "demo-tenant",
                        "resource": "pack",
                        "pack_id": pack_id,
                    },
                )
            _audit_record(request, "pack.publish", {"resource": "pack", "pack_id": pack_id})
            return {"status": "published", "pack_id": pack_id}
    raise HTTPException(status_code=404, detail="Pack not found")


@router.get("/api/boards/config")
@permission_required("portfolio.view")
async def get_board_config(workspace_id: str, entity: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(STORAGE_DIR / "board_configs.json", {"configs": []})
    for cfg in store.get("configs", []):
        if cfg.get("workspace_id") == workspace_id and cfg.get("entity") == entity:
            return cfg
    return {"workspace_id": workspace_id, "entity": entity, "view": "table", "columns": []}


@router.post("/api/boards/config")
@permission_required("config.manage")
async def save_board_config(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "board_configs.json"
    store = _load_store(path, {"configs": []})
    configs = [
        c
        for c in store.get("configs", [])
        if not (
            c.get("workspace_id") == payload.get("workspace_id")
            and c.get("entity") == payload.get("entity")
        )
    ]
    configs.append(payload)
    store["configs"] = configs
    _write_json(path, store)
    return payload


@router.get("/api/automations")
@permission_required("portfolio.view")
async def list_automations(request: Request) -> dict[str, Any]:
    _require_session(request)
    return _load_store(STORAGE_DIR / "automations.json", {"automations": [], "history": []})


@router.post("/api/automations")
@permission_required("config.manage")
async def create_automation(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "automations.json"
    store = _load_store(path, {"automations": [], "history": []})
    row = {
        "id": payload.get("id") or f"auto-{uuid4().hex[:8]}",
        "enabled": payload.get("enabled", True),
        **payload,
    }
    store.setdefault("automations", []).append(row)
    _write_json(path, store)
    return row


@router.post("/api/automations/{automation_id}/run")
@permission_required("config.manage")
async def run_automation(automation_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    path = STORAGE_DIR / "automations.json"
    store = _load_store(path, {"automations": [], "history": []})
    match = next((a for a in store.get("automations", []) if a.get("id") == automation_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Automation not found")
    run = {
        "id": f"run-{uuid4().hex[:8]}",
        "automation_id": automation_id,
        "status": "completed",
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
    store.setdefault("history", []).append(run)
    _write_json(path, store)
    if match.get("action") == "notify":
        nstore = _load_store(NOTIFICATIONS_STORE_PATH, {"notifications": []})
        _ensure_notifications(nstore, session.get("tenant_id") or "demo-tenant").append(
            {
                "id": f"ntf-{uuid4().hex[:8]}",
                "user_id": "*",
                "message": f"Automation {automation_id} executed",
                "read": False,
                "created_at": run["executed_at"],
            }
        )
        _write_json(NOTIFICATIONS_STORE_PATH, nstore)
    _audit_record(
        request, "automation.run", {"resource": "automation", "automation_id": automation_id}
    )
    return run

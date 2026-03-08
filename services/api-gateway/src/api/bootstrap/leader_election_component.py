from __future__ import annotations

from fastapi import FastAPI

from api.leader_election import build_leader_elector


def leader_readiness(app: FastAPI) -> dict[str, bool]:
    leader_elector = getattr(app.state, "leader_elector", None)
    leader_ready = leader_elector.is_leader if leader_elector else True
    return {"ready": leader_ready, "is_leader": leader_ready}


async def startup_leader_election(app: FastAPI) -> None:
    app.state.leader_elector = build_leader_elector("api-gateway")
    app.state.leader_elector.start()


async def shutdown_leader_election(app: FastAPI) -> None:
    leader_elector = getattr(app.state, "leader_elector", None)
    if leader_elector:
        leader_elector.stop()

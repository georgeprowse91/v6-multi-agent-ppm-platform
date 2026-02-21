from __future__ import annotations

from fastapi import FastAPI

from api.runtime_bootstrap import bootstrap_runtime_paths


def orchestrator_readiness(app: FastAPI) -> dict[str, bool]:
    orchestrator = getattr(app.state, "orchestrator", None)
    initialized = bool(orchestrator is not None and orchestrator.initialized)
    return {"ready": initialized, "initialized": initialized}


async def startup_orchestrator(app: FastAPI) -> None:
    bootstrap_runtime_paths()
    from orchestrator import AgentOrchestrator

    app.state.orchestrator = AgentOrchestrator()
    await app.state.orchestrator.initialize()


async def shutdown_orchestrator(app: FastAPI) -> None:
    orchestrator = getattr(app.state, "orchestrator", None)
    if orchestrator:
        await orchestrator.cleanup()

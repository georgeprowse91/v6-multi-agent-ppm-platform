from __future__ import annotations

from fastapi import FastAPI

from api.runtime_bootstrap import bootstrap_runtime_paths


def orchestrator_readiness(app: FastAPI) -> dict[str, bool]:
    orchestrator = getattr(app.state, "orchestrator", None)
    initialized = bool(orchestrator is not None and orchestrator.initialized)
    return {"ready": initialized, "initialized": initialized}


async def startup_orchestrator(app: FastAPI) -> None:
    import sys

    bootstrap_runtime_paths()
    from orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    await orch.initialize()
    app.state.orchestrator = orch
    # Mirror on module level so `patch("api.main.orchestrator", ...)` works in tests.
    _main = sys.modules.get("api.main")
    if _main is not None:
        _main.orchestrator = orch


async def shutdown_orchestrator(app: FastAPI) -> None:
    import sys

    orchestrator = getattr(app.state, "orchestrator", None)
    if orchestrator:
        await orchestrator.cleanup()
    _main = sys.modules.get("api.main")
    if _main is not None:
        _main.orchestrator = None

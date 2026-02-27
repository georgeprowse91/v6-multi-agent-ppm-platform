from __future__ import annotations

from observability.metrics import RequestMetricsMiddleware, configure_metrics
from observability.tracing import TraceMiddleware, configure_tracing
from security.api_governance import apply_api_governance, version_response_payload

from bootstrap import create_app

app = create_app()

configure_tracing("web-ui")
configure_metrics("web-ui")
app.add_middleware(TraceMiddleware, service_name="web-ui")
app.add_middleware(RequestMetricsMiddleware, service_name="web-ui")
apply_api_governance(app, service_name="web-ui")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "web-ui"}


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("web-ui")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8501, reload=False)

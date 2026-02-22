from __future__ import annotations

from observability.metrics import RequestMetricsMiddleware, configure_metrics
from observability.tracing import TraceMiddleware, configure_tracing

from bootstrap import create_app

app = create_app()

configure_tracing("web-ui")
configure_metrics("web-ui")
app.add_middleware(TraceMiddleware, service_name="web-ui")
app.add_middleware(RequestMetricsMiddleware, service_name="web-ui")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8501, reload=False)

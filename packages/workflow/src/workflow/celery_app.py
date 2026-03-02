from __future__ import annotations

import os

from celery import Celery


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def create_celery_app() -> Celery:
    broker_url = os.getenv("WORKFLOW_BROKER_URL") or os.getenv(
        "CELERY_BROKER_URL", "redis://localhost:6379/0"
    )
    result_backend = os.getenv("WORKFLOW_RESULT_BACKEND") or os.getenv(
        "CELERY_RESULT_BACKEND", broker_url
    )
    app = Celery("workflow_service", broker=broker_url, backend=result_backend)
    app.conf.update(
        task_default_queue=os.getenv("WORKFLOW_QUEUE", "workflow-service"),
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_always_eager=_bool_env("WORKFLOW_CELERY_EAGER"),
        task_eager_propagates=False,
    )
    return app


celery_app = create_celery_app()

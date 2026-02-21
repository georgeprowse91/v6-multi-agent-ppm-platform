from __future__ import annotations

from fastapi import FastAPI


# Central hook for future middleware registration.
def configure_application_middleware(app: FastAPI) -> None:
    _ = app

from __future__ import annotations

from api.bootstrap.connector_component import (
    connector_readiness,
    shutdown_connector_resources,
    startup_connector_resources,
)
from api.bootstrap.document_session_component import (
    document_session_readiness,
    shutdown_document_sessions,
    startup_document_sessions,
)
from api.bootstrap.leader_election_component import (
    leader_readiness,
    shutdown_leader_election,
    startup_leader_election,
)
from api.bootstrap.orchestrator_component import (
    orchestrator_readiness,
    shutdown_orchestrator,
    startup_orchestrator,
)
from api.bootstrap.registry import BootstrapRegistry, StartupComponent
from api.bootstrap.secret_rotation_component import (
    secret_rotation_readiness,
    shutdown_secret_rotation,
    startup_secret_rotation,
)


def build_default_bootstrap_registry() -> BootstrapRegistry:
    registry = BootstrapRegistry()
    registry.register(
        StartupComponent(
            name="orchestrator",
            startup=startup_orchestrator,
            shutdown=shutdown_orchestrator,
            readiness=orchestrator_readiness,
        )
    )
    registry.register(
        StartupComponent(
            name="connector_resources",
            startup=startup_connector_resources,
            shutdown=shutdown_connector_resources,
            readiness=connector_readiness,
        )
    )
    registry.register(
        StartupComponent(
            name="document_sessions",
            startup=startup_document_sessions,
            shutdown=shutdown_document_sessions,
            readiness=document_session_readiness,
            dependencies=("orchestrator",),
        )
    )
    registry.register(
        StartupComponent(
            name="secret_rotation",
            startup=startup_secret_rotation,
            shutdown=shutdown_secret_rotation,
            readiness=secret_rotation_readiness,
            dependencies=("connector_resources",),
            required=False,
        )
    )
    registry.register(
        StartupComponent(
            name="leader_election",
            startup=startup_leader_election,
            shutdown=shutdown_leader_election,
            readiness=leader_readiness,
        )
    )
    return registry

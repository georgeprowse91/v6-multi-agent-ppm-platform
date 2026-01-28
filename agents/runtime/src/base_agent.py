"""
Base Agent Class for Multi-Agent PPM Platform

This module provides the abstract base class that all agents inherit from.
"""

import logging
import os
import sys
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

OBSERVABILITY_ROOT = Path(__file__).resolve().parents[3] / "packages" / "observability" / "src"
if str(OBSERVABILITY_ROOT) not in sys.path:
    sys.path.insert(0, str(OBSERVABILITY_ROOT))

from pydantic import BaseModel  # noqa: E402

from observability.tracing import get_trace_id, start_agent_span  # noqa: E402

from agents.runtime.src.agent_catalog import get_catalog_id  # noqa: E402
from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from agents.runtime.src.models import (  # noqa: E402
    AgentPayload,
    AgentResponse,
    AgentResponseMetadata,
)
from agents.runtime.src.data_service import DataServiceClient  # noqa: E402
from agents.runtime.src.policy import (  # noqa: E402
    evaluate_policy_bundle,
    load_default_policy_bundle,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all PPM agents.

    All agents must implement the process() method and can optionally
    override lifecycle hooks (initialize, validate, cleanup).
    """

    def __init__(
        self,
        agent_id: str,
        config: dict[str, Any] | None = None,
        catalog_id: str | None = None,
    ):
        """
        Initialize the agent.

        Args:
            agent_id: Unique identifier for this agent instance
            config: Optional configuration dictionary
        """
        self.agent_id = agent_id
        self.config = config or {}
        self.catalog_id = catalog_id or self.config.get("catalog_id") or get_catalog_id(agent_id)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.initialized = False
        self.data_service: DataServiceClient | None = None
        data_service_url = self.config.get("data_service_url") or os.getenv("DATA_SERVICE_URL")
        if data_service_url:
            self.data_service = DataServiceClient.from_url(data_service_url)

    async def initialize(self) -> None:
        """
        Initialize agent resources (databases, connections, models, etc.).

        Called once before the agent starts processing requests.
        Override this method to perform setup tasks.
        """
        self.logger.info(f"Initializing agent {self.agent_id}")
        self.initialized = True

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """
        Validate input data before processing.

        Args:
            input_data: Input data to validate

        Returns:
            True if input is valid, False otherwise

        Override this method to add agent-specific validation.
        """
        return True

    @abstractmethod
    async def process(self, input_data: dict[str, Any]) -> Any:
        """
        Process the agent's core logic.

        This is the main method that must be implemented by all agents.

        Args:
            input_data: Input data for the agent to process

        Returns:
            Agent response payload as a dictionary or Pydantic model.

        Raises:
            ValueError: If input validation fails
            Exception: For agent-specific errors
        """
        pass

    async def cleanup(self) -> None:
        """
        Clean up agent resources.

        Called when the agent is shutting down.
        Override this method to perform cleanup tasks.
        """
        self.logger.info(f"Cleaning up agent {self.agent_id}")
        if self.data_service:
            await self.data_service.close()

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the full agent workflow with validation and error handling.

        Args:
            input_data: Input data for processing

        Returns:
            Dictionary containing:
                - success: Boolean indicating success/failure
                - data: Agent response data (if successful)
                - error: Error message (if failed)
                - metadata: Execution metadata (timing, agent_id, etc.)
        """
        start_time = datetime.utcnow()
        context = input_data.get("context", {})
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        catalog_id = self.catalog_id or self.agent_id
        trace_id = get_trace_id() or "unknown"

        policy_bundle = input_data.get(
            "policy_bundle",
            {
                "metadata": {
                    "version": self.get_config("policy_version", "1.0.0"),
                    "owner": self.get_config("policy_owner", self.agent_id),
                    "scope": "agent-execution",
                }
            },
        )
        policy_decision = evaluate_policy_bundle(policy_bundle, load_default_policy_bundle())
        audit_event = build_audit_event(
            tenant_id=tenant_id,
            action=f"{catalog_id}.policy.evaluated",
            outcome="denied" if policy_decision.decision == "deny" else "success",
            actor_id=self.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=policy_bundle.get("metadata", {}).get("name", catalog_id),
            resource_type="policy_bundle",
            metadata={"decision": policy_decision.decision, "reasons": policy_decision.reasons},
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
        emit_audit_event(audit_event)

        self._log_event(
            action="policy_evaluated",
            outcome="denied" if policy_decision.decision == "deny" else "success",
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        if policy_decision.decision == "deny":
            response = AgentResponse(
                success=False,
                error="Policy evaluation denied execution",
                metadata=AgentResponseMetadata(
                    agent_id=self.agent_id,
                    catalog_id=catalog_id,
                    timestamp=start_time.isoformat(),
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                    policy_reasons=policy_decision.reasons,
                ),
            )
            return response.model_dump()

        try:
            # Ensure agent is initialized
            if not self.initialized:
                await self.initialize()

            with start_agent_span(
                catalog_id,
                attributes={
                    "agent.id": self.agent_id,
                    "agent.catalog_id": catalog_id,
                    "tenant.id": tenant_id,
                    "correlation.id": correlation_id,
                },
            ):
                self._log_event(
                    action="execution_started",
                    outcome="success",
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                )

                # Validate input
                if not await self.validate_input(input_data):
                    self._log_event(
                        action="validation_failed",
                        outcome="failure",
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                    )
                    response = AgentResponse(
                        success=False,
                        error="Input validation failed",
                        metadata=AgentResponseMetadata(
                            agent_id=self.agent_id,
                            catalog_id=catalog_id,
                            timestamp=start_time.isoformat(),
                            correlation_id=correlation_id,
                            trace_id=trace_id,
                        ),
                    )
                    return response.model_dump()

                # Process the request
                self._log_event(
                    action="processing",
                    outcome="success",
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                )
                result = await self.process(input_data)
                payload = self._normalize_payload(result)

                # Calculate execution time
                execution_time = (datetime.utcnow() - start_time).total_seconds()

                self._log_event(
                    action="execution_completed",
                    outcome="success",
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                )

                response = AgentResponse(
                    success=True,
                    data=payload,
                    metadata=AgentResponseMetadata(
                        agent_id=self.agent_id,
                        catalog_id=catalog_id,
                        timestamp=start_time.isoformat(),
                        execution_time_seconds=execution_time,
                        correlation_id=correlation_id,
                        trace_id=trace_id,
                    ),
                )
                return response.model_dump()

        except Exception as e:
            self.logger.error(f"Error in agent {self.agent_id}: {str(e)}", exc_info=True)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._log_event(
                action="execution_failed",
                outcome="failure",
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

            response = AgentResponse(
                success=False,
                error=str(e),
                metadata=AgentResponseMetadata(
                    agent_id=self.agent_id,
                    catalog_id=catalog_id,
                    timestamp=start_time.isoformat(),
                    execution_time_seconds=execution_time,
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                ),
            )
            return response.model_dump()

    def get_capabilities(self) -> list[str]:
        """
        Return list of capabilities this agent provides.

        Override this method to declare agent capabilities.

        Returns:
            List of capability strings
        """
        return []

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def _log_event(self, *, action: str, outcome: str, tenant_id: str, correlation_id: str) -> None:
        self.logger.info(
            "agent_event",
            extra={
                "tenant_id": tenant_id,
                "trace_id": get_trace_id() or "unknown",
                "correlation_id": correlation_id,
                "agent_id": self.agent_id,
                "catalog_id": self.catalog_id or self.agent_id,
                "action": action,
                "outcome": outcome,
            },
        )

    def _normalize_payload(self, payload: Any) -> AgentPayload | None:
        if payload is None:
            return None
        if isinstance(payload, AgentPayload):
            return payload
        if isinstance(payload, BaseModel):
            return AgentPayload.model_validate(payload.model_dump())
        if isinstance(payload, dict):
            return AgentPayload.model_validate(payload)
        raise TypeError(f"Unsupported agent payload type: {type(payload).__name__}")

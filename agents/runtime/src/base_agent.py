"""
Base Agent Class for Multi-Agent PPM Platform

This module provides the abstract base class that all agents inherit from.
"""

import logging
import os
import sys
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OBSERVABILITY_ROOT = Path(__file__).resolve().parents[3] / "packages" / "observability" / "src"
if str(OBSERVABILITY_ROOT) not in sys.path:
    sys.path.insert(0, str(OBSERVABILITY_ROOT))

from observability.tracing import get_trace_id, start_agent_span  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from agents.runtime.src.agent_catalog import get_catalog_id  # noqa: E402
from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from agents.runtime.src.data_service import DataServiceClient  # noqa: E402
from agents.runtime.src.models import (  # noqa: E402
    AgentPayload,
    AgentResponse,
    AgentResponseMetadata,
)
from agents.runtime.src.policy import (  # noqa: E402
    evaluate_policy_bundle,
    load_default_policy_bundle,
)
from packages.memory_client import MemoryClient  # noqa: E402
from packages.llm.prompt_sanitizer import detect_injection, sanitize_prompt  # noqa: E402

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
        memory_client: MemoryClient | None = None,
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
        self.memory_client = memory_client
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
        start_time = datetime.now(timezone.utc)
        context = input_data.get("context", {})
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        persisted_context = self.load_context(correlation_id) or {}
        if persisted_context:
            context = {**persisted_context, **context}
            input_data = {**input_data, "context": context}
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

                input_data, injection_details = self._apply_prompt_sanitization(input_data)
                if injection_details["detected"]:
                    self._log_event(
                        action="prompt_injection_detected",
                        outcome="success",
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                        details=injection_details,
                    )
                    if injection_details["mode"] == "rejected":
                        response = AgentResponse(
                            success=False,
                            error="Input contains potentially unsafe prompt content.",
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
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

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
                self.save_context(correlation_id, {"last_output": response.model_dump()})
                return response.model_dump()

        except Exception as e:
            self.logger.error(f"Error in agent {self.agent_id}: {str(e)}", exc_info=True)
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._log_event(
                action="execution_failed",
                outcome="failure",
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

            # Avoid leaking internal details in non-development environments
            error_message = str(e) if os.getenv("ENVIRONMENT", "development") == "development" else e.__class__.__name__

            response = AgentResponse(
                success=False,
                error=error_message,
                metadata=AgentResponseMetadata(
                    agent_id=self.agent_id,
                    catalog_id=catalog_id,
                    timestamp=start_time.isoformat(),
                    execution_time_seconds=execution_time,
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                ),
            )
            self.save_context(correlation_id, {"last_error": response.model_dump()})
            return response.model_dump()

    def _memory_key(self, conversation_id: str) -> str:
        return f"{conversation_id}:{self.agent_id}"

    def save_context(self, conversation_id: str, data: dict[str, Any]) -> None:
        if self.memory_client is None:
            return
        self.memory_client.save_context(self._memory_key(conversation_id), data)

    def load_context(self, conversation_id: str) -> dict[str, Any] | None:
        if self.memory_client is None:
            return None
        return self.memory_client.load_context(self._memory_key(conversation_id))

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

    def _log_event(
        self,
        *,
        action: str,
        outcome: str,
        tenant_id: str,
        correlation_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        event_details = details or {}
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
                **event_details,
            },
        )

    def _apply_prompt_sanitization(self, input_data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        candidate_keys = self.get_config(
            "prompt_fields",
            ["prompt", "user_prompt", "query", "message", "input"],
        )
        allow_injection = bool(self.get_config("allow_injection", False))

        detected_fields: list[str] = []
        sanitized_fields: list[str] = []
        updated_input = dict(input_data)

        for key in candidate_keys:
            value = input_data.get(key)
            if not isinstance(value, str):
                continue
            if not detect_injection(value):
                continue

            detected_fields.append(key)
            if allow_injection:
                updated_input[key] = sanitize_prompt(value)
                sanitized_fields.append(key)

        details = {
            "detected": bool(detected_fields),
            "detected_fields": detected_fields,
            "sanitized_fields": sanitized_fields,
            "mode": "sanitized" if allow_injection else "rejected",
        }
        return updated_input, details

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

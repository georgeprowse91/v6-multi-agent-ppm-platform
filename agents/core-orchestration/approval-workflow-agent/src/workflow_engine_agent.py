"""
Workflow & Process Engine Agent

Purpose:
Orchestrates complex workflows and processes across the PPM platform, providing dynamic
workflow execution, state management, and human task coordination.

Specification: agents/core-orchestration/approval-workflow-agent/README.md
"""

import os
from pathlib import Path
from typing import Any

import yaml
from engine_infra import (
    emit_workflow_event,
    execute_task,
    find_event_subscriptions,
    invoke_logic_app,
    register_event_triggers,
    send_notification,
    trigger_compensation,
)
from engine_utils import event_matches_criteria
from workflow_actions import (
    handle_assign_task,
    handle_cancel_workflow,
    handle_complete_task,
    handle_define_workflow,
    handle_deploy_bpmn_workflow,
    handle_get_task_inbox,
    handle_get_workflow_instances,
    handle_get_workflow_status,
    handle_handle_event,
    handle_pause_workflow,
    handle_resume_workflow,
    handle_retry_failed_task,
    handle_start_workflow,
    handle_upload_bpmn_workflow,
)
from workflow_actions import (
    run_worker_once as _run_worker_once,
)
from workflow_spec import WorkflowSpecError
from workflow_state_store import WorkflowStateStore, build_workflow_state_store
from workflow_task_queue import WorkflowTaskQueue, build_task_queue

from agents.runtime import BaseAgent, ServiceBusEventBus, get_event_bus


class WorkflowEngineAgent(BaseAgent):
    """
    Workflow & Process Engine Agent - Orchestrates workflows and processes.

    Key Capabilities:
    - Process definition and modeling
    - Workflow execution and orchestration
    - Event-driven triggers
    - Human task management
    - Dynamic workflow adaptation
    - Process versioning and rollback
    - Monitoring and analytics
    - Exception handling and compensation
    """

    def __init__(self, agent_id: str = "approval-workflow-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        config = config or {}

        # Configuration parameters
        self.default_timeout_minutes = config.get("default_timeout_minutes", 60)
        self.max_retry_attempts = config.get("max_retry_attempts", 3)
        self.max_parallel_tasks = config.get("max_parallel_tasks", 10)
        self.worker_id = config.get("worker_id", os.getenv("WORKFLOW_WORKER_ID", self.agent_id))
        self.durable_config_path = Path(
            config.get(
                "durable_workflows_config",
                os.getenv("DURABLE_WORKFLOW_CONFIG", "ops/config/agents/approval-workflow-agent/durable_workflows.yaml"),
            )
        )
        self.monitoring_enabled = config.get("enable_monitoring", True)
        self.event_grid_enabled = config.get("enable_event_grid", True)
        self.logic_apps_endpoint = config.get("logic_apps_endpoint") or os.getenv(
            "LOGIC_APPS_ENDPOINT"
        )
        self.workflow_templates_path = Path(
            config.get(
                "workflow_templates_path",
                os.getenv("WORKFLOW_TEMPLATES_PATH", "ops/config/agents/approval-workflow-agent/workflow_templates.yaml"),
            )
        )
        self.rbac_policy = config.get(
            "rbac_policy",
            {
                "define_workflow": {"workflow_admin", "workflow_editor"},
                "start_workflow": {"workflow_admin", "workflow_operator"},
                "assign_task": {"workflow_admin", "workflow_operator"},
                "complete_task": {"workflow_admin", "workflow_operator"},
                "cancel_workflow": {"workflow_admin"},
                "pause_workflow": {"workflow_admin", "workflow_operator"},
                "resume_workflow": {"workflow_admin", "workflow_operator"},
                "retry_failed_task": {"workflow_admin", "workflow_operator"},
                "deploy_bpmn_workflow": {"workflow_admin", "workflow_editor"},
                "upload_bpmn_workflow": {"workflow_admin", "workflow_editor"},
            },
        )

        self.state_store: WorkflowStateStore = config.get("workflow_state_store") or (
            build_workflow_state_store(config)
        )
        self.task_queue: WorkflowTaskQueue = config.get("workflow_task_queue") or (
            build_task_queue(config)
        )

        # Cached state
        self.workflow_definitions = {}  # type: ignore
        self.workflow_instances = {}  # type: ignore
        self.task_assignments = {}  # type: ignore
        self.event_subscriptions = {}  # type: ignore
        self.durable_orchestrations = {}  # type: ignore
        self.event_bus = config.get("event_bus")
        if self.event_bus is None:
            service_bus_connection = config.get("service_bus_connection_string") or os.getenv(
                "SERVICE_BUS_CONNECTION_STRING"
            )
            if service_bus_connection:
                self.event_bus = ServiceBusEventBus(
                    connection_string=service_bus_connection,
                    topic_name=config.get("service_bus_topic", "ppm-events"),
                    subscription_name=config.get("service_bus_subscription"),
                )
            else:
                try:
                    self.event_bus = get_event_bus()
                except ValueError:
                    self.event_bus = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize workflow orchestration services and integrations."""
        await super().initialize()
        self.logger.info("Initializing Workflow & Process Engine Agent...")
        await self.state_store.initialize()
        await self._load_durable_workflows_config()
        await self._load_workflow_templates()

        if isinstance(self.event_bus, ServiceBusEventBus):
            self.event_bus.subscribe("workflow.triggers", self._handle_service_bus_trigger)
            await self.event_bus.start()

        self.logger.info("Workflow & Process Engine Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "define_workflow", "start_workflow", "get_workflow_status",
            "assign_task", "complete_task", "cancel_workflow",
            "pause_workflow", "resume_workflow", "handle_event",
            "retry_failed_task", "get_workflow_instances", "get_task_inbox",
            "deploy_bpmn_workflow", "upload_bpmn_workflow",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "define_workflow" and "workflow" not in input_data:
            self.logger.warning("Missing workflow definition")
            return False
        if action == "start_workflow" and "workflow_id" not in input_data:
            self.logger.warning("Missing workflow_id")
            return False
        if action == "deploy_bpmn_workflow" and "bpmn_xml" not in input_data:
            self.logger.warning("Missing BPMN XML payload")
            return False
        if action == "upload_bpmn_workflow" and "bpmn_xml" not in input_data and "bpmn_path" not in input_data:
            self.logger.warning("Missing BPMN XML payload or file path")
            return False

        return True

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process workflow and orchestration requests."""
        action = input_data.get("action", "get_workflow_instances")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )
        self._authorize_action(action, input_data)

        if action == "define_workflow":
            return await handle_define_workflow(self, tenant_id, input_data.get("workflow", {}))
        if action == "start_workflow":
            return await handle_start_workflow(
                self, tenant_id, input_data.get("workflow_id"),
                input_data.get("input_variables", {}),  # type: ignore
            )
        if action == "get_workflow_status":
            return await handle_get_workflow_status(
                self, tenant_id, input_data.get("instance_id"),  # type: ignore
            )
        if action == "assign_task":
            return await handle_assign_task(
                self, tenant_id, input_data.get("task_id"), input_data.get("assignee"),  # type: ignore
            )
        if action == "complete_task":
            return await handle_complete_task(
                self, tenant_id, input_data.get("task_id"), input_data.get("task_result", {}),  # type: ignore
            )
        if action == "cancel_workflow":
            return await handle_cancel_workflow(self, tenant_id, input_data.get("instance_id"))  # type: ignore
        if action == "pause_workflow":
            return await handle_pause_workflow(self, tenant_id, input_data.get("instance_id"))  # type: ignore
        if action == "resume_workflow":
            return await handle_resume_workflow(self, tenant_id, input_data.get("instance_id"))  # type: ignore
        if action == "handle_event":
            return await handle_handle_event(self, tenant_id, input_data.get("event", {}))
        if action == "retry_failed_task":
            return await handle_retry_failed_task(self, tenant_id, input_data.get("task_id"))  # type: ignore
        if action == "get_workflow_instances":
            return await handle_get_workflow_instances(self, tenant_id, input_data.get("filters", {}))
        if action == "get_task_inbox":
            return await handle_get_task_inbox(self, tenant_id, input_data.get("user_id"))  # type: ignore
        if action == "deploy_bpmn_workflow":
            return await handle_deploy_bpmn_workflow(
                self, tenant_id, input_data.get("bpmn_xml"), input_data.get("workflow_name"),  # type: ignore
            )
        if action == "upload_bpmn_workflow":
            return await handle_upload_bpmn_workflow(
                self, tenant_id, input_data.get("bpmn_xml"),
                input_data.get("bpmn_path"), input_data.get("workflow_name"),
            )
        raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Thin delegates to engine_infra (action handlers call these via agent)
    # ------------------------------------------------------------------

    async def _execute_task(self, tenant_id: str, instance_id: str, task: dict[str, Any]) -> None:
        await execute_task(self, tenant_id, instance_id, task)

    async def _trigger_compensation(self, tenant_id: str, instance: dict[str, Any], reason: str) -> None:
        await trigger_compensation(self, tenant_id, instance, reason)

    async def _register_event_triggers(self, tenant_id: str, workflow_id: str, triggers: list[dict[str, Any]]) -> None:
        await register_event_triggers(self, tenant_id, workflow_id, triggers)

    async def _find_event_subscriptions(self, tenant_id: str, event_type: str) -> list[dict[str, Any]]:
        return await find_event_subscriptions(self, tenant_id, event_type)

    async def _event_matches_criteria(self, event_data: dict[str, Any], criteria: dict[str, Any]) -> bool:
        return await event_matches_criteria(event_data, criteria)

    async def _emit_workflow_event(self, tenant_id: str, event_type: str, payload: dict[str, Any]) -> None:
        await emit_workflow_event(self, tenant_id, event_type, payload)

    async def _invoke_logic_app(self, tenant_id: str, assignment: dict[str, Any]) -> None:
        await invoke_logic_app(self, tenant_id, assignment)

    async def _send_notification(self, tenant_id: str, event_type: str, payload: dict[str, Any]) -> None:
        await send_notification(self, tenant_id, event_type, payload)

    # ------------------------------------------------------------------
    # Data access helpers
    # ------------------------------------------------------------------

    async def _load_definition(self, tenant_id: str, workflow_id: str) -> dict[str, Any] | None:
        cache_key = f"{tenant_id}:{workflow_id}"
        workflow = self.workflow_definitions.get(cache_key)
        if workflow:
            return workflow
        stored = await self.state_store.get_definition(tenant_id, workflow_id)
        if stored:
            self.workflow_definitions[cache_key] = stored
        return stored

    async def _load_instance(self, tenant_id: str, instance_id: str) -> dict[str, Any] | None:
        instance = self.workflow_instances.get(instance_id)
        if instance:
            return instance
        stored = await self.state_store.get_instance(tenant_id, instance_id)
        if stored:
            self.workflow_instances[instance_id] = stored
        return stored

    async def _load_task_assignment(self, tenant_id: str, task_id: str) -> dict[str, Any] | None:
        assignment = self.task_assignments.get(task_id)
        if assignment:
            return assignment
        stored = await self.state_store.get_task(tenant_id, task_id)
        if stored:
            self.task_assignments[task_id] = stored
        return stored

    # ------------------------------------------------------------------
    # Config loaders
    # ------------------------------------------------------------------

    async def _load_durable_workflows_config(self) -> None:
        if not self.durable_config_path.exists():
            self.logger.info("Durable workflow config not found", extra={"path": str(self.durable_config_path)})
            return
        config_payload = yaml.safe_load(self.durable_config_path.read_text()) or {}
        for workflow in config_payload.get("workflows", []):
            steps = workflow.get("steps", [])
            tasks, transitions = [], []
            for index, step in enumerate(steps):
                if index + 1 < len(steps):
                    transitions.append({"source": step.get("task_id"), "target": steps[index + 1].get("task_id")})
                tasks.append({
                    "task_id": step.get("task_id"), "name": step.get("name"),
                    "type": step.get("type", "automated"), "initial": index == 0,
                    "retry_policy": step.get("retry_policy"),
                    "compensation_task_id": step.get("compensation_task_id"),
                })
            await handle_define_workflow(self, "default", {
                "name": workflow.get("name") or workflow.get("workflow_id"),
                "description": workflow.get("description"),
                "tasks": tasks, "transitions": transitions,
                "definition_source": "durable_config", "version": workflow.get("version", 1),
            })

    async def _handle_service_bus_trigger(self, payload: dict[str, Any]) -> None:
        tenant_id = payload.get("tenant_id") or "default"
        await handle_handle_event(self, tenant_id, payload)

    async def _load_workflow_templates(self) -> None:
        if not self.workflow_templates_path.exists():
            self.logger.info("Workflow templates not found", extra={"path": str(self.workflow_templates_path)})
            return
        templates = yaml.safe_load(self.workflow_templates_path.read_text()) or {}
        for template in templates.get("templates", []):
            try:
                await handle_define_workflow(self, "default", template)
            except WorkflowSpecError as exc:
                self.logger.warning("Template invalid", extra={"template": template.get("name"), "error": str(exc)})

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------

    async def run_worker_once(self) -> dict[str, Any] | None:
        return await _run_worker_once(self)

    # ------------------------------------------------------------------
    # Cleanup / capabilities
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Workflow & Process Engine Agent...")
        if isinstance(self.event_bus, ServiceBusEventBus):
            await self.event_bus.stop()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "workflow_definition", "workflow_orchestration", "process_execution",
            "human_task_management", "event_driven_triggers", "dynamic_adaptation",
            "process_versioning", "exception_handling", "compensation",
            "workflow_monitoring", "bpmn_support", "state_management",
        ]

    def _authorize_action(self, action: str, input_data: dict[str, Any]) -> None:
        required_roles = self.rbac_policy.get(action)
        if not required_roles:
            return
        actor = input_data.get("actor") or {}
        roles = actor.get("roles") or input_data.get("context", {}).get("roles") or []
        if not roles:
            return
        if not set(roles).intersection(required_roles):
            raise PermissionError(f"Actor lacks required role for {action}")

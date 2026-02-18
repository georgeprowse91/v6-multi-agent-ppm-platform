"""
Agent 24: Workflow & Process Engine Agent

Purpose:
Orchestrates complex workflows and processes across the PPM platform, providing dynamic
workflow execution, state management, and human task coordination.

Specification: agents/operations-management/agent-24-workflow-process-engine/README.md
"""

import importlib
import importlib.util
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any
from xml.etree import ElementTree

import yaml
from observability.tracing import get_trace_id
from workflow_spec import WorkflowSpecError, load_workflow_spec, parse_workflow_spec
from workflow_state_store import WorkflowStateStore, build_workflow_state_store
from workflow_task_queue import WorkflowTaskQueue, build_task_message, build_task_queue

from agents.runtime import BaseAgent, get_event_bus, ServiceBusEventBus
from agents.runtime.src.audit import build_audit_event, emit_audit_event


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

    def __init__(self, agent_id: str = "agent_024", config: dict[str, Any] | None = None):
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
                os.getenv("DURABLE_WORKFLOW_CONFIG", "config/agent-24/durable_workflows.yaml"),
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
                os.getenv("WORKFLOW_TEMPLATES_PATH", "config/agent-24/workflow_templates.yaml"),
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

    async def initialize(self) -> None:
        """Initialize workflow engine, orchestration services, and integrations."""
        await super().initialize()
        self.logger.info("Initializing Workflow & Process Engine Agent...")
        await self.state_store.initialize()
        await self._load_durable_workflows_config()
        await self._load_workflow_templates()

        if isinstance(self.event_bus, ServiceBusEventBus):
            self.event_bus.subscribe("workflow.triggers", self._handle_service_bus_trigger)
            await self.event_bus.start()

        # Azure Durable Functions orchestration is represented by durable orchestrations
        # tracked in memory and persisted to the workflow state store.

        self.logger.info("Workflow & Process Engine Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "define_workflow",
            "start_workflow",
            "get_workflow_status",
            "assign_task",
            "complete_task",
            "cancel_workflow",
            "pause_workflow",
            "resume_workflow",
            "handle_event",
            "retry_failed_task",
            "get_workflow_instances",
            "get_task_inbox",
            "deploy_bpmn_workflow",
            "upload_bpmn_workflow",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "define_workflow":
            if "workflow" not in input_data:
                self.logger.warning("Missing workflow definition")
                return False

        elif action == "start_workflow":
            if "workflow_id" not in input_data:
                self.logger.warning("Missing workflow_id")
                return False
        elif action == "deploy_bpmn_workflow":
            if "bpmn_xml" not in input_data:
                self.logger.warning("Missing BPMN XML payload")
                return False
        elif action == "upload_bpmn_workflow":
            if "bpmn_xml" not in input_data and "bpmn_path" not in input_data:
                self.logger.warning("Missing BPMN XML payload or file path")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process workflow and orchestration requests.

        Args:
            input_data: {
                "action": "define_workflow" | "start_workflow" | "get_workflow_status" |
                          "assign_task" | "complete_task" | "cancel_workflow" |
                          "pause_workflow" | "resume_workflow" | "handle_event" |
                          "retry_failed_task" | "get_workflow_instances" | "get_task_inbox",
                          "deploy_bpmn_workflow",
                "workflow": Workflow definition (BPMN or JSON),
                "workflow_id": Workflow definition ID,
                "instance_id": Workflow instance ID,
                "task_id": Task identifier,
                "event": Event data,
                "input_variables": Workflow input variables,
                "task_result": Task completion result,
                "assignee": Task assignee,
                "filters": Query filters,
                "bpmn_xml": BPMN 2.0 XML string
            }

        Returns:
            Response based on action:
            - define_workflow: Workflow ID and validation results
            - start_workflow: Instance ID and initial state
            - get_workflow_status: Instance status and current state
            - assign_task: Assignment confirmation
            - complete_task: Task completion and next steps
            - cancel_workflow: Cancellation confirmation
            - pause_workflow: Pause confirmation
            - resume_workflow: Resume confirmation
            - handle_event: Event handling result
            - retry_failed_task: Retry result
            - get_workflow_instances: List of instances
            - get_task_inbox: User's pending tasks
            - deploy_bpmn_workflow: Deployment status for BPMN workflows
        """
        action = input_data.get("action", "get_workflow_instances")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )
        self._authorize_action(action, input_data)

        if action == "define_workflow":
            return await self._define_workflow(tenant_id, input_data.get("workflow", {}))

        elif action == "start_workflow":
            return await self._start_workflow(
                tenant_id,
                input_data.get("workflow_id"),
                input_data.get("input_variables", {}),  # type: ignore
            )

        elif action == "get_workflow_status":
            return await self._get_workflow_status(
                tenant_id, input_data.get("instance_id")  # type: ignore
            )

        elif action == "assign_task":
            return await self._assign_task(
                tenant_id, input_data.get("task_id"), input_data.get("assignee")  # type: ignore
            )

        elif action == "complete_task":
            return await self._complete_task(
                tenant_id, input_data.get("task_id"), input_data.get("task_result", {})  # type: ignore
            )

        elif action == "cancel_workflow":
            return await self._cancel_workflow(tenant_id, input_data.get("instance_id"))  # type: ignore

        elif action == "pause_workflow":
            return await self._pause_workflow(tenant_id, input_data.get("instance_id"))  # type: ignore

        elif action == "resume_workflow":
            return await self._resume_workflow(tenant_id, input_data.get("instance_id"))  # type: ignore

        elif action == "handle_event":
            return await self._handle_event(tenant_id, input_data.get("event", {}))

        elif action == "retry_failed_task":
            return await self._retry_failed_task(tenant_id, input_data.get("task_id"))  # type: ignore

        elif action == "get_workflow_instances":
            return await self._get_workflow_instances(tenant_id, input_data.get("filters", {}))

        elif action == "get_task_inbox":
            return await self._get_task_inbox(tenant_id, input_data.get("user_id"))  # type: ignore

        elif action == "deploy_bpmn_workflow":
            return await self._deploy_bpmn_workflow(
                tenant_id,
                input_data.get("bpmn_xml"),  # type: ignore
                input_data.get("workflow_name"),
            )
        elif action == "upload_bpmn_workflow":
            return await self._upload_bpmn_workflow(
                tenant_id,
                input_data.get("bpmn_xml"),
                input_data.get("bpmn_path"),
                input_data.get("workflow_name"),
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _define_workflow(
        self, tenant_id: str, workflow_config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Define new workflow process.

        Returns workflow ID and validation.
        """
        self.logger.info(f"Defining workflow: {workflow_config.get('name')}")

        normalized = self._normalize_workflow_definition(workflow_config)
        workflow_id = normalized.get("workflow_id") or await self._generate_workflow_id()

        # Validate workflow definition
        validation = await self._validate_workflow_definition(normalized)

        if not validation.get("valid"):
            return {"workflow_id": None, "status": "invalid", "errors": validation.get("errors")}

        # Parse workflow definition
        try:
            parsed_workflow = await self._parse_workflow_definition(normalized)
        except WorkflowSpecError as exc:
            return {"workflow_id": None, "status": "invalid", "errors": [str(exc)]}
        durable_orchestration = self._build_durable_orchestration(
            workflow_id,
            parsed_workflow.get("tasks", []),
            parsed_workflow.get("transitions", []),
            normalized.get("definition_source", "inline"),
        )

        # Create workflow definition
        workflow = {
            "workflow_id": workflow_id,
            "name": normalized.get("name"),
            "description": normalized.get("description"),
            "version": normalized.get("version", 1),
            "tasks": parsed_workflow.get("tasks", []),
            "events": parsed_workflow.get("events", []),
            "gateways": parsed_workflow.get("gateways", []),
            "transitions": parsed_workflow.get("transitions", []),
            "variables": normalized.get("variables", {}),
            "orchestration": durable_orchestration,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": normalized.get("author"),
            "definition_source": normalized.get("definition_source", "inline"),
            "task_sequence": [task.get("task_id") for task in parsed_workflow.get("tasks", [])],
            "dependencies": parsed_workflow.get("dependencies", {}),
        }

        # Store workflow definition
        self.workflow_definitions[workflow_id] = workflow
        await self.state_store.save_definition(tenant_id, workflow_id, workflow.copy())
        self.durable_orchestrations[workflow_id] = {
            "workflow_id": workflow_id,
            "definition": workflow,
            "steps": durable_orchestration.get("steps", []),
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        await self._register_event_triggers(
            tenant_id, workflow_id, normalized.get("event_triggers", [])
        )
        await self._emit_workflow_event(
            tenant_id,
            "workflow.defined",
            {"workflow_id": workflow_id, "name": workflow.get("name")},
        )


        return {
            "workflow_id": workflow_id,
            "name": workflow["name"],
            "version": workflow["version"],
            "tasks": len(workflow["tasks"]),
            "orchestration": durable_orchestration,
            "status": "defined",
        }

    async def _start_workflow(
        self, tenant_id: str, workflow_id: str, input_variables: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Start workflow instance.

        Returns instance ID and initial state.
        """
        self.logger.info(f"Starting workflow instance: {workflow_id}")

        # Get workflow definition
        workflow = await self._load_definition(tenant_id, workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # Generate instance ID
        instance_id = await self._generate_instance_id()

        # Initialize workflow state
        instance = {
            "instance_id": instance_id,
            "workflow_id": workflow_id,
            "tenant_id": tenant_id,
            "workflow_version": workflow.get("version"),
            "status": "running",
            "current_tasks": [],
            "completed_tasks": [],
            "failed_tasks": [],
            "completed_steps": [],
            "checkpoints": [],
            "last_checkpoint": None,
            "compensation_history": [],
            "orchestration": {
                "engine": "durable_functions",
                "orchestration_id": f"durable-{instance_id}",
                "workflow_orchestration": workflow.get("orchestration"),
            },
            "variables": input_variables,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "started_by": input_variables.get("requester"),
            "history": [],
        }

        # Store instance
        self.workflow_instances[instance_id] = instance
        await self.state_store.save_instance(tenant_id, instance_id, instance.copy())

        await self._emit_workflow_event(
            tenant_id,
            "workflow.started",
            {"workflow_id": workflow_id, "instance_id": instance_id},
        )

        # Execute first tasks
        initial_tasks = await self._get_initial_tasks(workflow)
        for task in initial_tasks:
            await self._execute_task(tenant_id, instance_id, task)


        return {
            "instance_id": instance_id,
            "workflow_id": workflow_id,
            "status": "running",
            "current_tasks": instance["current_tasks"],
            "started_at": instance["started_at"],
        }

    async def _get_workflow_status(self, tenant_id: str, instance_id: str) -> dict[str, Any]:
        """
        Get workflow instance status.

        Returns current state and progress.
        """
        self.logger.info(f"Getting workflow status: {instance_id}")

        instance = await self._load_instance(tenant_id, instance_id)
        if not instance:
            raise ValueError(f"Workflow instance not found: {instance_id}")

        # Calculate progress
        workflow_id = instance.get("workflow_id")
        workflow = await self._load_definition(tenant_id, workflow_id) if workflow_id else None
        total_tasks = len(workflow.get("tasks", [])) if workflow else 0
        completed_tasks = len(instance.get("completed_tasks", []))
        progress_pct = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        return {
            "instance_id": instance_id,
            "workflow_id": workflow_id,
            "status": instance.get("status"),
            "progress_percentage": progress_pct,
            "current_tasks": instance.get("current_tasks"),
            "completed_tasks": len(instance.get("completed_tasks", [])),
            "failed_tasks": len(instance.get("failed_tasks", [])),
            "started_at": instance.get("started_at"),
            "completed_at": instance.get("completed_at"),
        }

    async def _assign_task(self, tenant_id: str, task_id: str, assignee: str) -> dict[str, Any]:
        """
        Assign task to user.

        Returns assignment confirmation.
        """
        self.logger.info(f"Assigning task {task_id} to {assignee}")

        # Find task assignment
        assignment = await self._load_task_assignment(tenant_id, task_id)
        if not assignment:
            assignment = {"task_id": task_id, "status": "assigned"}
        assignment["assignee"] = assignee
        assignment["assigned_at"] = datetime.now(timezone.utc).isoformat()
        self.task_assignments[task_id] = assignment
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())
        await self._send_notification(
            tenant_id,
            "workflow.task.assigned",
            {
                "task_id": task_id,
                "assignee": assignee,
                "instance_id": assignment.get("instance_id"),
            },
        )


        return {"task_id": task_id, "assignee": assignee, "assigned_at": assignment["assigned_at"]}

    async def _complete_task(
        self, tenant_id: str, task_id: str, task_result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Complete workflow task.

        Returns completion status and next steps.
        """
        self.logger.info(f"Completing task: {task_id}")

        # Find task assignment
        assignment = await self._load_task_assignment(tenant_id, task_id)
        if not assignment:
            raise ValueError(f"Task assignment not found: {task_id}")

        # Update assignment
        assignment["status"] = "completed"
        assignment["completed_at"] = datetime.now(timezone.utc).isoformat()
        assignment["result"] = task_result
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())

        # Find workflow instance
        instance_id = assignment.get("instance_id")
        instance = None
        if instance_id:
            instance = await self._load_instance(tenant_id, instance_id)
        next_tasks: list[dict[str, Any]] = []
        if instance:
            # Move task from current to completed
            if task_id in instance.get("current_tasks", []):
                instance["current_tasks"].remove(task_id)
            instance.get("completed_tasks", []).append(task_id)
            instance.setdefault("completed_steps", []).append(task_id)
            checkpoint = {
                "task_id": task_id,
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            instance.setdefault("checkpoints", []).append(checkpoint)
            instance["last_checkpoint"] = task_id

            # Update variables with task result
            instance.get("variables", {}).update(task_result)

            # Determine next tasks
            next_tasks = await self._determine_next_tasks(instance, task_id)

            # Execute next tasks
            for next_task in next_tasks:
                await self._execute_task(tenant_id, instance_id, next_task)

            # Check if workflow is complete
            if await self._is_workflow_complete(instance):
                instance["status"] = "completed"
                instance["completed_at"] = datetime.now(timezone.utc).isoformat()
                await self._emit_workflow_event(
                    tenant_id,
                    "workflow.completed",
                    {"instance_id": instance_id, "workflow_id": instance.get("workflow_id")},
                )

        if instance_id and instance:
            await self.state_store.save_instance(tenant_id, instance_id, instance.copy())
            await self._emit_workflow_event(
                tenant_id,
                "workflow.task.completed",
                {"instance_id": instance_id, "task_id": task_id},
            )
            await self._send_notification(
                tenant_id,
                "workflow.task.completed",
                {"instance_id": instance_id, "task_id": task_id},
            )


        return {
            "task_id": task_id,
            "status": "completed",
            "next_tasks": [t.get("task_id") for t in next_tasks] if next_tasks else [],
            "workflow_status": instance.get("status") if instance else "unknown",
        }

    async def _cancel_workflow(self, tenant_id: str, instance_id: str) -> dict[str, Any]:
        """
        Cancel workflow instance.

        Returns cancellation confirmation.
        """
        self.logger.info(f"Canceling workflow: {instance_id}")

        instance = await self._load_instance(tenant_id, instance_id)
        if not instance:
            raise ValueError(f"Workflow instance not found: {instance_id}")

        await self._trigger_compensation(tenant_id, instance, reason="cancelled")

        # Update instance status
        instance["status"] = "cancelled"
        instance["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        await self.state_store.save_instance(tenant_id, instance_id, instance.copy())
        await self._emit_workflow_event(
            tenant_id, "workflow.cancelled", {"instance_id": instance_id}
        )
        await self._send_notification(
            tenant_id, "workflow.cancelled", {"instance_id": instance_id}
        )

        # Cancel pending tasks
        for task_id in instance.get("current_tasks", []):
            assignment = await self._load_task_assignment(tenant_id, task_id)
            if assignment:
                assignment["status"] = "cancelled"
                assignment["cancelled_at"] = datetime.now(timezone.utc).isoformat()
                self.task_assignments[task_id] = assignment
                await self.state_store.save_task(tenant_id, task_id, assignment.copy())


        return {
            "instance_id": instance_id,
            "status": "cancelled",
            "cancelled_at": instance["cancelled_at"],
        }

    async def _pause_workflow(self, tenant_id: str, instance_id: str) -> dict[str, Any]:
        """
        Pause workflow execution.

        Returns pause confirmation.
        """
        self.logger.info(f"Pausing workflow: {instance_id}")

        instance = await self._load_instance(tenant_id, instance_id)
        if not instance:
            raise ValueError(f"Workflow instance not found: {instance_id}")

        instance["status"] = "paused"
        instance["paused_at"] = datetime.now(timezone.utc).isoformat()
        await self.state_store.save_instance(tenant_id, instance_id, instance.copy())
        await self._emit_workflow_event(tenant_id, "workflow.paused", {"instance_id": instance_id})
        await self._send_notification(
            tenant_id, "workflow.paused", {"instance_id": instance_id}
        )


        return {"instance_id": instance_id, "status": "paused", "paused_at": instance["paused_at"]}

    async def _resume_workflow(self, tenant_id: str, instance_id: str) -> dict[str, Any]:
        """
        Resume paused workflow.

        Returns resume confirmation.
        """
        self.logger.info(f"Resuming workflow: {instance_id}")

        instance = await self._load_instance(tenant_id, instance_id)
        if not instance:
            raise ValueError(f"Workflow instance not found: {instance_id}")

        if instance.get("status") not in {"paused", "failed", "retrying", "compensating"}:
            raise ValueError(f"Workflow is not paused or failed: {instance_id}")

        instance["status"] = "running"
        instance["resumed_at"] = datetime.now(timezone.utc).isoformat()
        await self.state_store.save_instance(tenant_id, instance_id, instance.copy())
        await self._emit_workflow_event(tenant_id, "workflow.resumed", {"instance_id": instance_id})
        await self._send_notification(
            tenant_id, "workflow.resumed", {"instance_id": instance_id}
        )

        if instance.get("failed_tasks"):
            workflow_id = instance.get("workflow_id")
            workflow = await self._load_definition(tenant_id, workflow_id) if workflow_id else None
            if workflow:
                for task_id in list(instance.get("failed_tasks", [])):
                    task = next(
                        (item for item in workflow.get("tasks", []) if item.get("task_id") == task_id),
                        None,
                    )
                    if task:
                        await self._execute_task(tenant_id, instance_id, task)
                instance["failed_tasks"] = []
                await self.state_store.save_instance(tenant_id, instance_id, instance.copy())
            await self._resume_from_checkpoint(tenant_id, instance)

        return {
            "instance_id": instance_id,
            "status": "running",
            "resumed_at": instance["resumed_at"],
        }

    async def _handle_event(self, tenant_id: str, event: dict[str, Any]) -> dict[str, Any]:
        """
        Handle workflow event.

        Returns event handling result.
        """
        self.logger.info(f"Handling event: {event.get('event_type')}")

        event_type = event.get("event_type")
        event_data = event.get("data", {})
        if event_type in {"workflow.compensation.requested", "workflow.rollback.requested"}:
            return await self._handle_compensation_event(tenant_id, event_type, event_data)

        # Find subscribed workflows
        subscribed_workflows = await self._find_event_subscriptions(tenant_id, event_type)  # type: ignore

        triggered_instances = []
        for subscription in subscribed_workflows:
            # Check if event matches subscription criteria
            if await self._event_matches_criteria(event_data, subscription.get("criteria", {})):
                # Start or advance workflow
                if subscription.get("action") == "start":
                    result = await self._start_workflow(
                        tenant_id, subscription.get("workflow_id"), event_data  # type: ignore
                    )
                    triggered_instances.append(result.get("instance_id"))
                elif subscription.get("action") == "trigger_task":
                    instance_id = event_data.get("instance_id")
                    task_id = event_data.get("task_id") or subscription.get("task_id")
                    if not instance_id or not task_id:
                        continue
                    instance = await self._load_instance(tenant_id, instance_id)
                    if not instance:
                        continue
                    workflow_id = instance.get("workflow_id") or subscription.get("workflow_id")
                    workflow = await self._load_definition(tenant_id, workflow_id)
                    if not workflow:
                        continue
                    task = next(
                        (
                            item
                            for item in workflow.get("tasks", [])
                            if item.get("task_id") == task_id
                        ),
                        None,
                    )
                    if not task:
                        continue
                    await self._execute_task(tenant_id, instance_id, task)
                    triggered_instances.append(instance_id)

        await self._emit_workflow_event(
            tenant_id,
            "workflow.event.handled",
            {"event_type": event_type, "instances_triggered": triggered_instances},
        )

        return {
            "event_type": event_type,
            "subscriptions_matched": len(subscribed_workflows),
            "instances_triggered": len(triggered_instances),
            "triggered_instances": triggered_instances,
        }

    async def _retry_failed_task(self, tenant_id: str, task_id: str) -> dict[str, Any]:
        """
        Retry failed task.

        Returns retry result.
        """
        self.logger.info(f"Retrying failed task: {task_id}")

        assignment = await self._load_task_assignment(tenant_id, task_id)
        if not assignment:
            raise ValueError(f"Task assignment not found: {task_id}")

        # Check retry count
        retry_count = assignment.get("retry_count", 0)
        if retry_count >= self.max_retry_attempts:
            return {
                "task_id": task_id,
                "status": "max_retries_exceeded",
                "retry_count": retry_count,
            }

        # Reset task status
        assignment["status"] = "assigned"
        assignment["retry_count"] = retry_count + 1
        assignment["retried_at"] = datetime.now(timezone.utc).isoformat()
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())
        await self._send_notification(
            tenant_id,
            "workflow.task.retrying",
            {"task_id": task_id, "retry_count": assignment["retry_count"]},
        )

        # Re-execute task
        assignment.get("instance_id")

        return {"task_id": task_id, "status": "retrying", "retry_count": assignment["retry_count"]}

    async def _get_workflow_instances(
        self, tenant_id: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Get workflow instances with filters.

        Returns list of instances.
        """
        self.logger.info("Retrieving workflow instances")

        # Filter instances
        filtered = []
        instances = await self.state_store.list_instances(tenant_id)
        for instance in instances:
            instance_id = instance.get("instance_id")
            if await self._matches_instance_filters(instance, filters):
                filtered.append(
                    {
                        "instance_id": instance_id,
                        "workflow_id": instance.get("workflow_id"),
                        "status": instance.get("status"),
                        "started_at": instance.get("started_at"),
                        "completed_at": instance.get("completed_at"),
                    }
                )

        # Sort by start date
        filtered.sort(key=lambda x: x.get("started_at", ""), reverse=True)

        return {"total_instances": len(filtered), "instances": filtered, "filters": filters}

    async def _get_task_inbox(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        """
        Get user's pending tasks.

        Returns task list.
        """
        self.logger.info(f"Retrieving task inbox for user: {user_id}")

        # Find tasks assigned to user
        user_tasks = []
        tasks = await self.state_store.list_tasks(tenant_id, assignee=user_id, status="assigned")
        for assignment in tasks:
            if assignment.get("assignee") == user_id and assignment.get("status") == "assigned":
                user_tasks.append(
                    {
                        "task_id": assignment.get("task_id"),
                        "instance_id": assignment.get("instance_id"),
                        "assigned_at": assignment.get("assigned_at"),
                        "task_type": assignment.get("task_type"),
                    }
                )

        # Sort by assigned date
        user_tasks.sort(key=lambda x: x.get("assigned_at", ""))

        return {"user_id": user_id, "pending_tasks": len(user_tasks), "tasks": user_tasks}

    async def _deploy_bpmn_workflow(
        self, tenant_id: str, bpmn_xml: str, workflow_name: str | None = None
    ) -> dict[str, Any]:
        workflow_config = {
            "name": workflow_name or "BPMN Workflow",
            "description": "BPMN 2.0 deployment",
            "bpmn_xml": bpmn_xml,
            "definition_source": "bpmn_upload",
        }
        result = await self._define_workflow(tenant_id, workflow_config)
        return {
            "workflow_id": result.get("workflow_id"),
            "status": result.get("status"),
            "tasks": result.get("tasks"),
            "definition_source": "bpmn_upload",
        }

    async def _upload_bpmn_workflow(
        self,
        tenant_id: str,
        bpmn_xml: str | None,
        bpmn_path: str | None,
        workflow_name: str | None = None,
    ) -> dict[str, Any]:
        if not bpmn_xml and bpmn_path:
            bpmn_xml = Path(bpmn_path).read_text(encoding="utf-8")
        if not bpmn_xml:
            raise ValueError("BPMN XML payload is required")
        return await self._deploy_bpmn_workflow(tenant_id, bpmn_xml, workflow_name)

    async def _handle_compensation_event(
        self, tenant_id: str, event_type: str, event_data: dict[str, Any]
    ) -> dict[str, Any]:
        instance_id = event_data.get("instance_id")
        if not instance_id:
            raise ValueError("instance_id is required for compensation events")
        instance = await self._load_instance(tenant_id, instance_id)
        if not instance:
            raise ValueError(f"Workflow instance not found: {instance_id}")
        await self._trigger_compensation(tenant_id, instance, reason=event_type)
        return {"instance_id": instance_id, "status": "compensation_triggered"}

    # Helper methods

    async def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"WF-{timestamp}"

    async def _generate_instance_id(self) -> str:
        """Generate unique instance ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"INST-{timestamp}"

    async def _validate_workflow_definition(
        self, workflow_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate workflow definition."""
        errors = []

        if not workflow_config.get("name"):
            errors.append("Workflow name is required")

        if (
            not workflow_config.get("tasks")
            and not workflow_config.get("steps")
            and not workflow_config.get("bpmn_xml")
        ):
            errors.append("Workflow must have at least one task")

        return {"valid": len(errors) == 0, "errors": errors}

    async def _parse_workflow_definition(self, workflow_config: dict[str, Any]) -> dict[str, Any]:
        """Parse workflow definition."""
        bpmn_xml = workflow_config.get("bpmn_xml")
        if bpmn_xml:
            return self._parse_bpmn_xml(bpmn_xml)
        if workflow_config.get("steps"):
            parsed = parse_workflow_spec(workflow_config)
            return {
                "tasks": parsed.tasks,
                "events": workflow_config.get("events", []),
                "gateways": workflow_config.get("gateways", []),
                "transitions": parsed.transitions,
                "dependencies": parsed.dependencies,
            }
        return {
            "tasks": workflow_config.get("tasks", []),
            "events": workflow_config.get("events", []),
            "gateways": workflow_config.get("gateways", []),
            "transitions": workflow_config.get("transitions", []),
            "dependencies": workflow_config.get("dependencies", {}),
        }

    def _parse_bpmn_xml(self, bpmn_xml: str) -> dict[str, Any]:
        """Parse BPMN 2.0 XML into workflow tasks and transitions."""
        parsed = self._parse_bpmn_with_bpmn_python(bpmn_xml)
        if parsed:
            return parsed
        root = ElementTree.fromstring(bpmn_xml)
        namespace = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}

        def _findall(tag: str) -> list[ElementTree.Element]:
            return root.findall(f".//bpmn:{tag}", namespaces=namespace)

        tasks: list[dict[str, Any]] = []
        transitions: list[dict[str, Any]] = []

        start_events = {event.get("id") for event in _findall("startEvent") if event.get("id")}

        for task_type, internal_type in [
            ("userTask", "human"),
            ("serviceTask", "automated"),
            ("scriptTask", "automated"),
            ("task", "automated"),
        ]:
            for task in _findall(task_type):
                task_id = task.get("id")
                if not task_id:
                    continue
                tasks.append(
                    {
                        "task_id": task_id,
                        "name": task.get("name"),
                        "type": internal_type,
                        "initial": False,
                    }
                )

        for flow in _findall("sequenceFlow"):
            source = flow.get("sourceRef")
            target = flow.get("targetRef")
            if source and target:
                transitions.append({"source": source, "target": target})

        initial_targets = {
            flow.get("targetRef")
            for flow in _findall("sequenceFlow")
            if flow.get("sourceRef") in start_events
        }
        for task in tasks:
            if task.get("task_id") in initial_targets:
                task["initial"] = True

        dependencies: dict[str, list[str]] = {}
        incoming: dict[str, set[str]] = {}
        for transition in transitions:
            source = transition.get("source")
            target = transition.get("target")
            if source and target:
                incoming.setdefault(target, set()).add(source)
        for task_id, deps in incoming.items():
            dependencies[task_id] = sorted(deps)
        return {
            "tasks": tasks,
            "events": [],
            "gateways": [],
            "transitions": transitions,
            "dependencies": dependencies,
        }

    def _parse_bpmn_with_bpmn_python(self, bpmn_xml: str) -> dict[str, Any] | None:
        spec = importlib.util.find_spec("bpmn_python")
        if not spec:
            return None
        bpmn_diagram_rep = importlib.import_module("bpmn_python.bpmn_diagram_rep")
        if not hasattr(bpmn_diagram_rep, "BpmnDiagramGraph"):
            return None
        diagram = bpmn_diagram_rep.BpmnDiagramGraph()
        if hasattr(diagram, "load_diagram_from_xml_string"):
            diagram.load_diagram_from_xml_string(bpmn_xml)
        else:
            return None
        tasks = []
        for node_id, node in diagram.diagram_graph.nodes.items():
            node_type = node[1].get("type")
            if node_type in {"userTask", "serviceTask", "scriptTask", "task"}:
                tasks.append(
                    {
                        "task_id": node_id,
                        "name": node[1].get("name"),
                        "type": "human" if node_type == "userTask" else "automated",
                        "initial": False,
                    }
                )
        transitions = [
            {"source": edge[0], "target": edge[1]} for edge in diagram.diagram_graph.edges
        ]
        incoming: dict[str, set[str]] = {}
        for transition in transitions:
            source = transition.get("source")
            target = transition.get("target")
            if source and target:
                incoming.setdefault(target, set()).add(source)
        dependencies = {task_id: sorted(deps) for task_id, deps in incoming.items()}
        return {
            "tasks": tasks,
            "events": [],
            "gateways": [],
            "transitions": transitions,
            "dependencies": dependencies,
        }

    async def _get_initial_tasks(self, workflow: dict[str, Any]) -> list[dict[str, Any]]:
        """Get initial tasks to execute."""
        tasks = workflow.get("tasks", [])
        initial = [t for t in tasks if t.get("initial", False)]
        if initial:
            return initial
        return tasks[:1]

    def _build_durable_orchestration(
        self,
        workflow_id: str,
        tasks: list[dict[str, Any]],
        transitions: list[dict[str, Any]],
        source: str,
    ) -> dict[str, Any]:
        transition_map: dict[str, list[str]] = {}
        for transition in transitions:
            source_id = transition.get("source")
            target_id = transition.get("target")
            if not source_id or not target_id:
                continue
            transition_map.setdefault(source_id, []).append(target_id)

        steps = []
        for index, task in enumerate(tasks):
            task_id = task.get("task_id")
            if not task_id:
                continue
            next_tasks = transition_map.get(task_id)
            if not next_tasks and index + 1 < len(tasks):
                next_tasks = [tasks[index + 1].get("task_id")]
            steps.append(
                {
                    "step_id": f"{workflow_id}:{task_id}",
                    "task_id": task_id,
                    "name": task.get("name"),
                    "type": task.get("type"),
                    "retry_policy": task.get("retry_policy"),
                    "compensation_task_id": task.get("compensation_task_id"),
                    "next": [target for target in (next_tasks or []) if target],
                }
            )

        return {
            "workflow_id": workflow_id,
            "engine": "azure_durable_functions",
            "source": source,
            "steps": steps,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _load_durable_workflows_config(self) -> None:
        if not self.durable_config_path.exists():
            self.logger.info(
                "Durable workflow config not found", extra={"path": str(self.durable_config_path)}
            )
            return
        config_payload = yaml.safe_load(self.durable_config_path.read_text()) or {}
        workflows = config_payload.get("workflows", [])
        for workflow in workflows:
            steps = workflow.get("steps", [])
            tasks = []
            transitions = []
            for index, step in enumerate(steps):
                if index + 1 < len(steps):
                    transitions.append(
                        {"source": step.get("task_id"), "target": steps[index + 1].get("task_id")}
                    )
                tasks.append(
                    {
                        "task_id": step.get("task_id"),
                        "name": step.get("name"),
                        "type": step.get("type", "automated"),
                        "initial": index == 0,
                        "retry_policy": step.get("retry_policy"),
                        "compensation_task_id": step.get("compensation_task_id"),
                    }
                )
            workflow_config = {
                "name": workflow.get("name") or workflow.get("workflow_id"),
                "description": workflow.get("description"),
                "tasks": tasks,
                "transitions": transitions,
                "definition_source": "durable_config",
                "version": workflow.get("version", 1),
            }
            await self._define_workflow("default", workflow_config)

    async def _handle_service_bus_trigger(self, payload: dict[str, Any]) -> None:
        tenant_id = payload.get("tenant_id") or "default"
        await self._handle_event(tenant_id, payload)

    async def _trigger_compensation(
        self, tenant_id: str, instance: dict[str, Any], reason: str
    ) -> None:
        workflow_id = instance.get("workflow_id")
        workflow = await self._load_definition(tenant_id, workflow_id) if workflow_id else None
        if not workflow:
            return
        compensation_tasks = []
        completed_steps = list(instance.get("completed_steps", []))
        failed_steps = list(instance.get("failed_tasks", []))
        for task_id in completed_steps + failed_steps:
            task = next(
                (item for item in workflow.get("tasks", []) if item.get("task_id") == task_id),
                None,
            )
            if task and task.get("compensation_task_id"):
                comp_task = next(
                    (
                        item
                        for item in workflow.get("tasks", [])
                        if item.get("task_id") == task.get("compensation_task_id")
                    ),
                    None,
                )
                if comp_task:
                    compensation_tasks.append(comp_task)

        if not compensation_tasks:
            return

        instance["status"] = "compensating"
        await self.state_store.save_instance(tenant_id, instance["instance_id"], instance.copy())
        await self._emit_workflow_event(
            tenant_id,
            "workflow.compensation.started",
            {"instance_id": instance["instance_id"], "reason": reason},
        )
        await self._send_notification(
            tenant_id,
            "workflow.compensation.started",
            {"instance_id": instance["instance_id"], "reason": reason},
        )

        for task in compensation_tasks:
            await self._execute_task(tenant_id, instance["instance_id"], task)

        instance.setdefault("compensation_history", []).append(
            {
                "reason": reason,
                "tasks": [task.get("task_id") for task in compensation_tasks],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        await self.state_store.save_instance(tenant_id, instance["instance_id"], instance.copy())
        await self._emit_workflow_event(
            tenant_id,
            "workflow.compensation.completed",
            {"instance_id": instance["instance_id"], "tasks": [t.get("task_id") for t in compensation_tasks]},
        )
        await self._send_notification(
            tenant_id,
            "workflow.compensation.completed",
            {"instance_id": instance["instance_id"], "tasks": [t.get("task_id") for t in compensation_tasks]},
        )

    async def _execute_task(self, tenant_id: str, instance_id: str, task: dict[str, Any]) -> None:
        """Execute workflow task."""
        task_id = task.get("task_id")

        # Create task assignment
        assignment = {
            "task_id": task_id,
            "instance_id": instance_id,
            "task_type": task.get("type"),
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "task_payload": task,
            "retry_policy": task.get("retry_policy"),
            "compensation_task_id": task.get("compensation_task_id"),
        }
        self.task_assignments[task_id] = assignment
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())

        # Add to instance current tasks
        instance = await self._load_instance(tenant_id, instance_id)
        if instance:
            instance.get("current_tasks", []).append(task_id)
            await self.state_store.save_instance(tenant_id, instance_id, instance.copy())

        await self.task_queue.publish_task(
            build_task_message(
                tenant_id=tenant_id,
                instance_id=instance_id,
                task_id=task_id,
                task_type=task.get("type"),
                payload={"workflow_id": instance.get("workflow_id") if instance else None},
            )
        )

    async def _determine_next_tasks(
        self, instance: dict[str, Any], completed_task_id: str
    ) -> list[dict[str, Any]]:
        """Determine next tasks to execute."""
        workflow_id = instance.get("workflow_id")
        tenant_id = instance.get("tenant_id") or "default"
        workflow = await self._load_definition(tenant_id, workflow_id) if workflow_id else None
        if not workflow:
            return []
        transitions = workflow.get("transitions", [])
        tasks = workflow.get("tasks", [])
        task_map = {task.get("task_id"): task for task in tasks if task.get("task_id")}
        dependencies = workflow.get("dependencies", {})

        candidates = [
            transition
            for transition in transitions
            if transition.get("source") == completed_task_id
        ]
        next_task_ids: list[str] = []
        for transition in candidates:
            condition = transition.get("condition")
            if condition and not self._evaluate_condition(condition, instance.get("variables", {})):
                continue
            target = transition.get("target")
            if target:
                next_task_ids.extend(
                    self._resolve_virtual_targets(target, task_map, transitions, instance)
                )

        if not next_task_ids:
            sequence = workflow.get("task_sequence", [])
            if completed_task_id in sequence:
                index = sequence.index(completed_task_id)
                if index + 1 < len(sequence):
                    next_task_ids = [sequence[index + 1]]

        completed_steps = set(instance.get("completed_steps", []))
        completed_steps.update(instance.get("completed_tasks", []))
        filtered = []
        for task_id in dict.fromkeys(next_task_ids):
            if task_id in instance.get("current_tasks", []):
                continue
            if task_id in completed_steps:
                continue
            deps = set(dependencies.get(task_id, []))
            if deps and not deps.issubset(completed_steps):
                continue
            task = task_map.get(task_id)
            if task:
                filtered.append(task)
        return filtered

    def _resolve_virtual_targets(
        self,
        target_id: str,
        task_map: dict[str, dict[str, Any]],
        transitions: list[dict[str, Any]],
        instance: dict[str, Any],
        depth: int = 0,
    ) -> list[str]:
        if depth > 8:
            return []
        target = task_map.get(target_id)
        if not target:
            return []
        if target.get("type") not in {"decision", "parallel", "loop"}:
            return [target_id]
        instance.setdefault("completed_steps", [])
        if target_id not in instance["completed_steps"]:
            instance["completed_steps"].append(target_id)
        next_ids = []
        for transition in transitions:
            if transition.get("source") != target_id:
                continue
            condition = transition.get("condition")
            if condition and not self._evaluate_condition(condition, instance.get("variables", {})):
                continue
            if transition.get("target"):
                next_ids.extend(
                    self._resolve_virtual_targets(
                        transition["target"], task_map, transitions, instance, depth + 1
                    )
                )
        return next_ids

    def _evaluate_condition(self, condition: dict[str, Any], variables: dict[str, Any]) -> bool:
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        resolved = self._resolve_reference(field, variables)

        if operator == "exists":
            return resolved is not None
        if operator == "equals":
            return resolved == value
        if operator == "not_equals":
            return resolved != value
        if operator == "greater_than":
            return resolved is not None and resolved > value
        if operator == "less_than":
            return resolved is not None and resolved < value
        if operator == "contains":
            if isinstance(resolved, (list, tuple, set)):
                return value in resolved
            if isinstance(resolved, str):
                return str(value) in resolved
        return False

    def _resolve_reference(self, value: Any, variables: dict[str, Any]) -> Any:
        if not isinstance(value, str):
            return value
        if not value.startswith("$."):
            return value
        path = value[2:].split(".")
        current: Any = {"vars": variables}
        for part in path:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    async def _is_workflow_complete(self, instance: dict[str, Any]) -> bool:
        """Check if workflow is complete."""
        if instance.get("status") != "running":
            return False
        if instance.get("current_tasks"):
            return False
        workflow_id = instance.get("workflow_id")
        tenant_id = instance.get("tenant_id") or "default"
        workflow = await self._load_definition(tenant_id, workflow_id) if workflow_id else None
        if not workflow:
            return False
        completed = set(instance.get("completed_tasks", []))
        task_ids = {
            task.get("task_id")
            for task in workflow.get("tasks", [])
            if task.get("task_id") and task.get("type") not in {"decision", "parallel", "loop"}
        }
        return bool(task_ids) and task_ids.issubset(completed)

    async def _find_event_subscriptions(
        self, tenant_id: str, event_type: str
    ) -> list[dict[str, Any]]:
        """Find workflows subscribed to event type."""
        subscriptions = await self.state_store.list_subscriptions(tenant_id, event_type=event_type)
        for subscription in subscriptions:
            if subscription.get("subscription_id"):
                self.event_subscriptions[subscription["subscription_id"]] = subscription
        return subscriptions

    async def _register_event_triggers(
        self, tenant_id: str, workflow_id: str, triggers: list[dict[str, Any]]
    ) -> None:
        """Register event triggers for a workflow definition."""
        for trigger in triggers:
            subscription_id = f"SUB-{len(self.event_subscriptions) + 1}"
            subscription = {
                "subscription_id": subscription_id,
                "workflow_id": workflow_id,
                "event_type": trigger.get("event_type"),
                "criteria": trigger.get("criteria", {}),
                "action": trigger.get("action", "start"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "task_id": trigger.get("task_id"),
            }
            self.event_subscriptions[subscription_id] = subscription
            await self.state_store.save_subscription(
                tenant_id, subscription_id, subscription.copy()
            )

    async def _emit_workflow_event(
        self, tenant_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Emit workflow events for audit/analytics."""
        event_id = f"WF-EVT-{len(self.workflow_instances) + 1}"
        event_record = {
            "event_id": event_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.state_store.save_event(tenant_id, event_id, event_record)
        audit_event = build_audit_event(
            tenant_id=tenant_id,
            action=event_type,
            outcome="success",
            actor_id=self.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=payload.get("instance_id") or payload.get("workflow_id") or event_id,
            resource_type="workflow_event",
            metadata={"event_id": event_id},
            trace_id=get_trace_id(),
        )
        emit_audit_event(audit_event)
        if self.event_bus:
            await self.event_bus.publish("workflow.events", event_record)
            await self.event_bus.publish("workflow.notifications", event_record)
        await self._emit_monitor_telemetry(tenant_id, event_type, payload)
        await self._emit_event_grid_event(tenant_id, event_type, payload)

    async def _emit_monitor_telemetry(
        self, tenant_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        if not self.monitoring_enabled:
            return
        telemetry_payload = {
            "tenant_id": tenant_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "workflow_engine_agent",
        }
        if self.event_bus:
            await self.event_bus.publish("azure.monitor.telemetry", telemetry_payload)

    async def _emit_event_grid_event(
        self, tenant_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        if not self.event_grid_enabled:
            return
        event_grid_payload = {
            "tenant_id": tenant_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "workflow_engine_agent",
        }
        if self.event_bus:
            await self.event_bus.publish("azure.eventgrid.events", event_grid_payload)

    async def _invoke_logic_app(self, tenant_id: str, assignment: dict[str, Any]) -> None:
        payload = {
            "tenant_id": tenant_id,
            "task_id": assignment.get("task_id"),
            "instance_id": assignment.get("instance_id"),
            "payload": assignment.get("task_payload", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if self.logic_apps_endpoint:
            self.logger.info(
                "Logic Apps invocation scheduled",
                extra={"endpoint": self.logic_apps_endpoint, "task_id": assignment.get("task_id")},
            )
        if self.event_bus:
            await self.event_bus.publish("logic.apps.invocations", payload)

    async def _event_matches_criteria(
        self, event_data: dict[str, Any], criteria: dict[str, Any]
    ) -> bool:
        """Check if event matches subscription criteria."""
        if not criteria:
            return True

        if not isinstance(criteria, dict):
            self.logger.warning("Invalid event criteria definition: expected object", extra={"criteria": criteria})
            return False

        for field_path, condition in criteria.items():
            exists, actual_value = self._extract_field_path(event_data, field_path)
            if not self._evaluate_criterion(field_path, exists, actual_value, condition):
                return False

        return True

    def _extract_field_path(self, payload: dict[str, Any], field_path: str) -> tuple[bool, Any]:
        """Resolve dotted field paths from event payloads (for example metadata.tenant_id)."""
        if not field_path:
            return False, None

        current: Any = payload
        for segment in field_path.split("."):
            if isinstance(current, dict) and segment in current:
                current = current[segment]
                continue
            if isinstance(current, list) and segment.isdigit():
                index = int(segment)
                if 0 <= index < len(current):
                    current = current[index]
                    continue
            return False, None

        return True, current

    def _evaluate_criterion(
        self, field_path: str, exists: bool, actual_value: Any, condition: Any
    ) -> bool:
        if isinstance(condition, dict):
            for operator, expected_value in condition.items():
                if not self._evaluate_operator(field_path, operator, expected_value, exists, actual_value):
                    return False
            return True

        if not exists:
            return False
        return actual_value == condition

    def _evaluate_operator(
        self,
        field_path: str,
        operator: str,
        expected_value: Any,
        exists: bool,
        actual_value: Any,
    ) -> bool:
        if operator == "exists":
            if not isinstance(expected_value, bool):
                self.logger.warning(
                    "Invalid exists operator value", extra={"field": field_path, "expected": expected_value}
                )
                return False
            return exists == expected_value

        if not exists:
            return False

        if operator == "eq":
            return actual_value == expected_value
        if operator == "ne":
            return actual_value != expected_value

        if operator == "in":
            if not isinstance(expected_value, list):
                self.logger.warning(
                    "Invalid in operator value", extra={"field": field_path, "expected": expected_value}
                )
                return False
            if isinstance(actual_value, list):
                return any(item in expected_value for item in actual_value)
            return actual_value in expected_value

        if operator == "not_in":
            if not isinstance(expected_value, list):
                self.logger.warning(
                    "Invalid not_in operator value", extra={"field": field_path, "expected": expected_value}
                )
                return False
            if isinstance(actual_value, list):
                return all(item not in expected_value for item in actual_value)
            return actual_value not in expected_value

        if operator in {"gt", "gte", "lt", "lte"}:
            compared = self._coerce_comparable(actual_value, expected_value)
            if compared is None:
                self.logger.warning(
                    "Invalid comparison criterion",
                    extra={"field": field_path, "operator": operator, "actual": actual_value, "expected": expected_value},
                )
                return False
            left, right = compared
            if operator == "gt":
                return left > right
            if operator == "gte":
                return left >= right
            if operator == "lt":
                return left < right
            return left <= right

        self.logger.warning(
            "Unsupported criteria operator", extra={"field": field_path, "operator": operator}
        )
        return False

    def _coerce_comparable(self, actual_value: Any, expected_value: Any) -> tuple[Any, Any] | None:
        actual_dt = self._parse_datetime(actual_value)
        expected_dt = self._parse_datetime(expected_value)
        if actual_dt and expected_dt:
            return actual_dt, expected_dt

        actual_num = self._parse_number(actual_value)
        expected_num = self._parse_number(expected_value)
        if actual_num is not None and expected_num is not None:
            return actual_num, expected_num

        return None

    def _parse_number(self, value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _parse_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

        if not isinstance(value, str):
            return None

        candidate = value.strip()
        if not candidate:
            return None

        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"

        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return None

        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    async def _matches_instance_filters(
        self, instance: dict[str, Any], filters: dict[str, Any]
    ) -> bool:
        """Check if instance matches filters."""
        if "status" in filters and instance.get("status") != filters["status"]:
            return False

        if "workflow_id" in filters and instance.get("workflow_id") != filters["workflow_id"]:
            return False

        return True

    async def _load_definition(self, tenant_id: str, workflow_id: str) -> dict[str, Any] | None:
        workflow = self.workflow_definitions.get(workflow_id)
        if workflow:
            return workflow
        stored = await self.state_store.get_definition(tenant_id, workflow_id)
        if stored:
            self.workflow_definitions[workflow_id] = stored
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

    async def run_worker_once(self) -> dict[str, Any] | None:
        message = await self.task_queue.reserve_task()
        if not message:
            return None
        result: dict[str, Any]
        try:
            result = await self._handle_task_message(message)
            await self.task_queue.ack_task(message.message_id)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            await self._mark_task_failed(
                message.tenant_id,
                message.task_id,
                message.instance_id,
                reason=str(exc),
            )
            await self.task_queue.fail_task(message.message_id, str(exc))
            result = {
                "task_id": message.task_id,
                "instance_id": message.instance_id,
                "status": "failed",
                "error": str(exc),
            }
        return result

    async def _handle_task_message(self, message: Any) -> dict[str, Any]:
        tenant_id = message.tenant_id
        task_id = message.task_id
        assignment = await self._load_task_assignment(tenant_id, task_id)
        if not assignment:
            raise ValueError(f"Task assignment not found: {task_id}")
        if assignment.get("status") == "retrying" and assignment.get("next_retry_at"):
            next_retry = datetime.fromisoformat(assignment["next_retry_at"])
            if datetime.now(timezone.utc) < next_retry:
                await self.task_queue.publish_task(
                    build_task_message(
                        tenant_id=tenant_id,
                        instance_id=message.instance_id,
                        task_id=task_id,
                        task_type=assignment.get("task_type"),
                        payload=assignment.get("task_payload", {}),
                    )
                )
                return {
                    "task_id": task_id,
                    "status": "retry_scheduled",
                    "next_retry_at": assignment["next_retry_at"],
                }
        assignment["status"] = "in_progress"
        assignment["worker_id"] = self.worker_id
        assignment["started_at"] = datetime.now(timezone.utc).isoformat()
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())

        task_payload = assignment.get("task_payload", {})
        if task_payload.get("simulate_failure"):
            raise RuntimeError("Simulated task failure")

        if assignment.get("task_type") == "automated":
            result_payload = await self._execute_automated_task(tenant_id, assignment)
            result = await self._complete_task(tenant_id, task_id, result_payload)
            return result
        if assignment.get("task_type") == "logic_app":
            await self._invoke_logic_app(tenant_id, assignment)
            result = await self._complete_task(
                tenant_id, task_id, {"status": "logic_app_triggered"}
            )
            return result

        assignment["status"] = "assigned"
        assignment["assigned_at"] = datetime.now(timezone.utc).isoformat()
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())
        return {"task_id": task_id, "status": "assigned"}

    async def _mark_task_failed(
        self, tenant_id: str, task_id: str, instance_id: str, reason: str
    ) -> None:
        assignment = await self._load_task_assignment(tenant_id, task_id)
        if assignment:
            assignment["status"] = "failed"
            assignment["failed_at"] = datetime.now(timezone.utc).isoformat()
            assignment["failure_reason"] = reason
            retry_policy = assignment.get("retry_policy") or {}
            retry_count = assignment.get("retry_count", 0)
            max_attempts = retry_policy.get("max_attempts", self.max_retry_attempts)
            backoff_seconds = retry_policy.get("backoff_seconds", 0)
            if retry_count < max_attempts:
                assignment["retry_count"] = retry_count + 1
                assignment["status"] = "retrying"
                if backoff_seconds:
                    assignment["next_retry_at"] = (
                        datetime.now(timezone.utc)
                        + timedelta(seconds=int(backoff_seconds))
                    ).isoformat()
                await self.state_store.save_task(tenant_id, task_id, assignment.copy())
                await self._send_notification(
                    tenant_id,
                    "workflow.task.retrying",
                    {
                        "task_id": task_id,
                        "instance_id": instance_id,
                        "retry_count": assignment["retry_count"],
                    },
                )
                await self.task_queue.publish_task(
                    build_task_message(
                        tenant_id=tenant_id,
                        instance_id=instance_id,
                        task_id=task_id,
                        task_type=assignment.get("task_type"),
                        payload=assignment.get("task_payload", {}),
                    )
                )
            else:
                await self.state_store.save_task(tenant_id, task_id, assignment.copy())
                await self._send_notification(
                    tenant_id,
                    "workflow.task.failed",
                    {
                        "task_id": task_id,
                        "instance_id": instance_id,
                        "reason": reason,
                    },
                )

        instance = await self._load_instance(tenant_id, instance_id)
        if instance:
            instance.setdefault("failed_tasks", []).append(task_id)
            instance.setdefault("checkpoints", []).append(
                {
                    "task_id": task_id,
                    "status": "failed",
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            instance["last_checkpoint"] = task_id
            if assignment and assignment.get("status") == "retrying":
                instance["status"] = "retrying"
            else:
                instance["status"] = "failed"
            await self.state_store.save_instance(tenant_id, instance_id, instance.copy())
            if instance["status"] == "failed":
                await self._trigger_compensation(tenant_id, instance, reason=reason)
                await self._send_notification(
                    tenant_id,
                    "workflow.failed",
                    {"instance_id": instance_id, "reason": reason},
                )

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Workflow & Process Engine Agent...")
        if isinstance(self.event_bus, ServiceBusEventBus):
            await self.event_bus.stop()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "workflow_definition",
            "workflow_orchestration",
            "process_execution",
            "human_task_management",
            "event_driven_triggers",
            "dynamic_adaptation",
            "process_versioning",
            "exception_handling",
            "compensation",
            "workflow_monitoring",
            "bpmn_support",
            "state_management",
        ]

    def _authorize_action(self, action: str, input_data: dict[str, Any]) -> None:
        required_roles = self.rbac_policy.get(action)
        if not required_roles:
            return
        actor = input_data.get("actor") or {}
        roles = actor.get("roles") or input_data.get("context", {}).get("roles") or []
        if not set(roles).intersection(required_roles):
            raise PermissionError(f"Actor lacks required role for {action}")

    def _normalize_workflow_definition(self, workflow_config: dict[str, Any]) -> dict[str, Any]:
        if "workflow_spec" in workflow_config:
            spec = load_workflow_spec(workflow_config["workflow_spec"])
            workflow_config = {**workflow_config, **spec}
        if "workflow_yaml" in workflow_config:
            spec = load_workflow_spec(workflow_config["workflow_yaml"])
            workflow_config = {**workflow_config, **spec}
        metadata = workflow_config.get("metadata") or {}
        if metadata:
            workflow_config.setdefault("name", metadata.get("name"))
            workflow_config.setdefault("description", metadata.get("description"))
            workflow_config.setdefault("version", metadata.get("version"))
            workflow_config.setdefault("owner", metadata.get("owner"))
        return workflow_config

    async def _resume_from_checkpoint(self, tenant_id: str, instance: dict[str, Any]) -> None:
        if instance.get("status") != "running":
            return
        if instance.get("current_tasks"):
            return
        workflow_id = instance.get("workflow_id")
        workflow = await self._load_definition(tenant_id, workflow_id) if workflow_id else None
        if not workflow:
            return
        last_checkpoint = instance.get("last_checkpoint")
        if not last_checkpoint:
            return
        next_tasks = await self._determine_next_tasks(instance, last_checkpoint)
        for next_task in next_tasks:
            await self._execute_task(tenant_id, instance["instance_id"], next_task)

    async def _execute_automated_task(
        self, tenant_id: str, assignment: dict[str, Any]
    ) -> dict[str, Any]:
        task_payload = assignment.get("task_payload", {})
        if task_payload.get("callable") or task_payload.get("script"):
            result = await self._execute_script_task(tenant_id, assignment)
            return {"status": "script_completed", "result": result}
        return {"status": "auto_completed"}

    async def _execute_script_task(
        self, tenant_id: str, assignment: dict[str, Any]
    ) -> dict[str, Any]:
        callable_path = assignment.get("task_payload", {}).get("callable")
        if not callable_path:
            raise ValueError("Script task requires callable path")
        module_name, _, function_name = callable_path.partition(":")
        if not module_name or not function_name:
            raise ValueError("Callable must be in 'module:function' format")
        module = importlib.import_module(module_name)
        func = getattr(module, function_name, None)
        if not callable(func):
            raise ValueError(f"Callable {callable_path} not found")
        return func(
            {
                "tenant_id": tenant_id,
                "instance_id": assignment.get("instance_id"),
                "task_id": assignment.get("task_id"),
                "payload": assignment.get("task_payload", {}),
                "variables": assignment.get("task_payload", {}).get("variables", {}),
            }
        )

    async def _send_notification(
        self, tenant_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        notification = {
            "tenant_id": tenant_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "workflow_engine_agent",
        }
        if self.event_bus:
            await self.event_bus.publish("workflow.notifications", notification)

    async def _load_workflow_templates(self) -> None:
        if not self.workflow_templates_path.exists():
            self.logger.info(
                "Workflow templates not found", extra={"path": str(self.workflow_templates_path)}
            )
            return
        templates = yaml.safe_load(self.workflow_templates_path.read_text()) or {}
        for template in templates.get("templates", []):
            try:
                await self._define_workflow("default", template)
            except WorkflowSpecError as exc:
                self.logger.warning(
                    "Template invalid", extra={"template": template.get("name"), "error": str(exc)}
                )

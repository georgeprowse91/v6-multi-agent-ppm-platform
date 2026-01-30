"""
Agent 24: Workflow & Process Engine Agent

Purpose:
Orchestrates complex workflows and processes across the PPM platform, providing dynamic
workflow execution, state management, and human task coordination.

Specification: agents/operations-management/agent-24-workflow-process-engine/README.md
"""

from datetime import datetime
import os
from typing import Any

from observability.tracing import get_trace_id

from agents.runtime import BaseAgent, InMemoryEventBus
from agents.runtime.src.audit import build_audit_event, emit_audit_event

from workflow_state_store import WorkflowStateStore, build_workflow_state_store
from workflow_task_queue import WorkflowTaskQueue, build_task_message, build_task_queue


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
        self.event_bus = config.get("event_bus")
        if self.event_bus is None:
            self.event_bus = InMemoryEventBus()

    async def initialize(self) -> None:
        """Initialize workflow engine, orchestration services, and integrations."""
        await super().initialize()
        self.logger.info("Initializing Workflow & Process Engine Agent...")
        await self.state_store.initialize()

        # Future work: Initialize Azure Durable Functions for orchestration
        # Future work: Set up Azure Logic Apps for workflow execution
        # Future work: Initialize Azure Service Bus for event-driven triggers
        # Future work: Connect to BPMN modeling tools (Camunda Modeler)
        # Future work: Initialize Azure Functions for task execution
        # Future work: Set up Azure Monitor for workflow monitoring
        # Future work: Connect to task management systems (Jira, Azure Boards)
        # Future work: Initialize Approval Workflow Agent integration
        # Future work: Set up Azure Event Grid for workflow events

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
                "workflow": Workflow definition (BPMN or JSON),
                "workflow_id": Workflow definition ID,
                "instance_id": Workflow instance ID,
                "task_id": Task identifier,
                "event": Event data,
                "input_variables": Workflow input variables,
                "task_result": Task completion result,
                "assignee": Task assignee,
                "filters": Query filters
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
        """
        action = input_data.get("action", "get_workflow_instances")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )

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
            return await self._get_workflow_instances(
                tenant_id, input_data.get("filters", {})
            )

        elif action == "get_task_inbox":
            return await self._get_task_inbox(tenant_id, input_data.get("user_id"))  # type: ignore

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

        # Generate workflow ID
        workflow_id = await self._generate_workflow_id()

        # Validate workflow definition
        validation = await self._validate_workflow_definition(workflow_config)

        if not validation.get("valid"):
            return {"workflow_id": None, "status": "invalid", "errors": validation.get("errors")}

        # Parse workflow definition
        parsed_workflow = await self._parse_workflow_definition(workflow_config)

        # Create workflow definition
        workflow = {
            "workflow_id": workflow_id,
            "name": workflow_config.get("name"),
            "description": workflow_config.get("description"),
            "version": 1,
            "tasks": parsed_workflow.get("tasks", []),
            "events": parsed_workflow.get("events", []),
            "gateways": parsed_workflow.get("gateways", []),
            "transitions": parsed_workflow.get("transitions", []),
            "variables": workflow_config.get("variables", {}),
            "created_at": datetime.utcnow().isoformat(),
            "created_by": workflow_config.get("author"),
        }

        # Store workflow definition
        self.workflow_definitions[workflow_id] = workflow
        await self.state_store.save_definition(tenant_id, workflow_id, workflow.copy())

        await self._register_event_triggers(
            tenant_id, workflow_id, workflow_config.get("event_triggers", [])
        )
        await self._emit_workflow_event(
            tenant_id,
            "workflow.defined",
            {"workflow_id": workflow_id, "name": workflow.get("name")},
        )

        # Future work: Store in database
        # Future work: Import/export BPMN XML if provided
        # Future work: Publish workflow.defined event

        return {
            "workflow_id": workflow_id,
            "name": workflow["name"],
            "version": workflow["version"],
            "tasks": len(workflow["tasks"]),
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
            "workflow_version": workflow.get("version"),
            "status": "running",
            "current_tasks": [],
            "completed_tasks": [],
            "failed_tasks": [],
            "variables": input_variables,
            "started_at": datetime.utcnow().isoformat(),
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

        # Future work: Store in database
        # Future work: Publish workflow.started event

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
        assignment["assigned_at"] = datetime.utcnow().isoformat()
        self.task_assignments[task_id] = assignment
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())

        # Future work: Store in database
        # Future work: Send notification to assignee
        # Future work: Publish task.assigned event

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
        assignment["completed_at"] = datetime.utcnow().isoformat()
        assignment["result"] = task_result
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())

        # Find workflow instance
        instance_id = assignment.get("instance_id")
        instance = self.workflow_instances.get(instance_id)
        if instance:
            # Move task from current to completed
            if task_id in instance.get("current_tasks", []):
                instance["current_tasks"].remove(task_id)
            instance.get("completed_tasks", []).append(task_id)

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
                instance["completed_at"] = datetime.utcnow().isoformat()

        if instance_id and instance:
            await self.state_store.save_instance(tenant_id, instance_id, instance.copy())
            await self._emit_workflow_event(
                tenant_id,
                "workflow.task.completed",
                {"instance_id": instance_id, "task_id": task_id},
            )

        # Future work: Store in database
        # Future work: Publish task.completed event

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

        # Execute compensation tasks if defined
        # Future work: Implement compensation logic

        # Update instance status
        instance["status"] = "cancelled"
        instance["cancelled_at"] = datetime.utcnow().isoformat()
        await self.state_store.save_instance(tenant_id, instance_id, instance.copy())
        await self._emit_workflow_event(
            tenant_id, "workflow.cancelled", {"instance_id": instance_id}
        )

        # Cancel pending tasks
        for task_id in instance.get("current_tasks", []):
            assignment = await self._load_task_assignment(tenant_id, task_id)
            if assignment:
                assignment["status"] = "cancelled"
                assignment["cancelled_at"] = datetime.utcnow().isoformat()
                self.task_assignments[task_id] = assignment
                await self.state_store.save_task(tenant_id, task_id, assignment.copy())

        # Future work: Store in database
        # Future work: Publish workflow.cancelled event

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
        instance["paused_at"] = datetime.utcnow().isoformat()
        await self.state_store.save_instance(tenant_id, instance_id, instance.copy())
        await self._emit_workflow_event(tenant_id, "workflow.paused", {"instance_id": instance_id})

        # Future work: Store in database
        # Future work: Publish workflow.paused event

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

        if instance.get("status") != "paused":
            raise ValueError(f"Workflow is not paused: {instance_id}")

        instance["status"] = "running"
        instance["resumed_at"] = datetime.utcnow().isoformat()
        await self.state_store.save_instance(tenant_id, instance_id, instance.copy())
        await self._emit_workflow_event(tenant_id, "workflow.resumed", {"instance_id": instance_id})

        # Future work: Store in database
        # Future work: Publish workflow.resumed event
        # Future work: Resume pending tasks

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
                        (item for item in workflow.get("tasks", []) if item.get("task_id") == task_id),
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
        assignment["retried_at"] = datetime.utcnow().isoformat()
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())

        # Re-execute task
        assignment.get("instance_id")
        # Future work: Re-execute task logic

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

    # Helper methods

    async def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"WF-{timestamp}"

    async def _generate_instance_id(self) -> str:
        """Generate unique instance ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"INST-{timestamp}"

    async def _validate_workflow_definition(
        self, workflow_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate workflow definition."""
        errors = []

        if not workflow_config.get("name"):
            errors.append("Workflow name is required")

        if not workflow_config.get("tasks"):
            errors.append("Workflow must have at least one task")

        return {"valid": len(errors) == 0, "errors": errors}

    async def _parse_workflow_definition(self, workflow_config: dict[str, Any]) -> dict[str, Any]:
        """Parse workflow definition."""
        # Future work: Parse BPMN XML if provided
        return {
            "tasks": workflow_config.get("tasks", []),
            "events": workflow_config.get("events", []),
            "gateways": workflow_config.get("gateways", []),
            "transitions": workflow_config.get("transitions", []),
        }

    async def _get_initial_tasks(self, workflow: dict[str, Any]) -> list[dict[str, Any]]:
        """Get initial tasks to execute."""
        tasks = workflow.get("tasks", [])
        return [t for t in tasks if t.get("initial", False)][:1]

    async def _execute_task(self, tenant_id: str, instance_id: str, task: dict[str, Any]) -> None:
        """Execute workflow task."""
        task_id = task.get("task_id")

        # Create task assignment
        assignment = {
            "task_id": task_id,
            "instance_id": instance_id,
            "task_type": task.get("type"),
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "task_payload": task,
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
        # Future work: Implement transition logic based on gateways
        return []

    async def _is_workflow_complete(self, instance: dict[str, Any]) -> bool:
        """Check if workflow is complete."""
        return len(instance.get("current_tasks", [])) == 0 and instance.get("status") == "running"

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
                "created_at": datetime.utcnow().isoformat(),
                "task_id": trigger.get("task_id"),
            }
            self.event_subscriptions[subscription_id] = subscription
            await self.state_store.save_subscription(tenant_id, subscription_id, subscription.copy())

    async def _emit_workflow_event(
        self, tenant_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Emit workflow events for audit/analytics."""
        event_id = f"WF-EVT-{len(self.workflow_instances) + 1}"
        event_record = {
            "event_id": event_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
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

    async def _event_matches_criteria(
        self, event_data: dict[str, Any], criteria: dict[str, Any]
    ) -> bool:
        """Check if event matches subscription criteria."""
        # Future work: Implement criteria matching
        return True

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
        except Exception as exc:
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
        assignment["status"] = "in_progress"
        assignment["worker_id"] = self.worker_id
        assignment["started_at"] = datetime.utcnow().isoformat()
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())

        task_payload = assignment.get("task_payload", {})
        if task_payload.get("simulate_failure"):
            raise RuntimeError("Simulated task failure")

        if assignment.get("task_type") == "automated":
            result = await self._complete_task(tenant_id, task_id, {"status": "auto_completed"})
            return result

        assignment["status"] = "assigned"
        assignment["assigned_at"] = datetime.utcnow().isoformat()
        await self.state_store.save_task(tenant_id, task_id, assignment.copy())
        return {"task_id": task_id, "status": "assigned"}

    async def _mark_task_failed(
        self, tenant_id: str, task_id: str, instance_id: str, reason: str
    ) -> None:
        assignment = await self._load_task_assignment(tenant_id, task_id)
        if assignment:
            assignment["status"] = "failed"
            assignment["failed_at"] = datetime.utcnow().isoformat()
            assignment["failure_reason"] = reason
            await self.state_store.save_task(tenant_id, task_id, assignment.copy())

        instance = await self._load_instance(tenant_id, instance_id)
        if instance:
            instance.setdefault("failed_tasks", []).append(task_id)
            instance["status"] = "failed"
            await self.state_store.save_instance(tenant_id, instance_id, instance.copy())

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Workflow & Process Engine Agent...")
        # Future work: Close database connections
        # Future work: Close orchestration connections
        # Future work: Cancel running workflows if needed

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

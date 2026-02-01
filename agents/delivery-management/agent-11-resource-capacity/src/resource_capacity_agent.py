"""
Agent 11: Resource & Capacity Management Agent

Purpose:
Manages both supply of resources (people, equipment, skills) and demand from projects
and programs. Provides real-time insights into availability, utilization and skill gaps.

Specification: agents/delivery-management/agent-11-resource-capacity/README.md
"""

import asyncio
import hashlib
import importlib.util
import json
import math
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from data_quality.rules import evaluate_quality_rules
from events import ResourceAllocationCreatedEvent
from observability.tracing import get_trace_id

from agents.common.connector_integration import CalendarIntegrationService, DatabaseStorageService
from agents.common.integration_services import ForecastingModel
from agents.common.scenario import ScenarioEngine
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore


class ResourceCapacityRepository:
    def __init__(self, database_url: str | None) -> None:
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        self.EmployeeProfileRecord = None
        self.CapacityAllocationRecord = None
        if database_url:
            from sqlalchemy import JSON, Float, String, create_engine, select
            from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

            class Base(DeclarativeBase):
                pass

            class EmployeeProfileRecord(Base):  # type: ignore
                __tablename__ = "employee_profiles"

                employee_id: Mapped[str] = mapped_column(String(128), primary_key=True)
                source_system: Mapped[str] = mapped_column(String(64), default="unknown")
                profile: Mapped[dict[str, Any]] = mapped_column(JSON)
                updated_at: Mapped[str] = mapped_column(String(64))

            class CapacityAllocationRecord(Base):  # type: ignore
                __tablename__ = "capacity_allocations"

                allocation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
                employee_id: Mapped[str] = mapped_column(String(128))
                project_id: Mapped[str] = mapped_column(String(128))
                start_date: Mapped[str] = mapped_column(String(32))
                end_date: Mapped[str] = mapped_column(String(32))
                allocation_percentage: Mapped[float] = mapped_column(Float)
                source_system: Mapped[str] = mapped_column(String(64), default="agent")
                metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

            class ResourceScheduleRecord(Base):  # type: ignore
                __tablename__ = "resource_schedules"

                resource_id: Mapped[str] = mapped_column(String(128), primary_key=True)
                schedule: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
                availability: Mapped[float] = mapped_column(Float, default=1.0)
                updated_at: Mapped[str] = mapped_column(String(64))

            class ResourceForecastRecord(Base):  # type: ignore
                __tablename__ = "resource_forecasts"

                forecast_id: Mapped[str] = mapped_column(String(128), primary_key=True)
                forecast_type: Mapped[str] = mapped_column(String(64))
                payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
                created_at: Mapped[str] = mapped_column(String(64))

            class ResourcePerformanceRecord(Base):  # type: ignore
                __tablename__ = "resource_performance_scores"

                resource_id: Mapped[str] = mapped_column(String(128), primary_key=True)
                score: Mapped[float] = mapped_column(Float, default=0.0)
                metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
                updated_at: Mapped[str] = mapped_column(String(64))

            self.engine = create_engine(database_url)
            Base.metadata.create_all(self.engine)
            self.session_factory = sessionmaker(self.engine)
            self.EmployeeProfileRecord = EmployeeProfileRecord
            self.CapacityAllocationRecord = CapacityAllocationRecord
            self.ResourceScheduleRecord = ResourceScheduleRecord
            self.ResourceForecastRecord = ResourceForecastRecord
            self.ResourcePerformanceRecord = ResourcePerformanceRecord
            self._select = select

    def is_enabled(self) -> bool:
        return self.engine is not None and self.session_factory is not None

    def upsert_employee_profile(self, profile: dict[str, Any]) -> None:
        if not self.is_enabled():
            return
        employee_id = profile.get("employee_id")
        if not employee_id:
            return
        source_system = profile.get("source_system", "unknown")
        updated_at = datetime.utcnow().isoformat()
        with self.session_factory() as session:  # type: ignore[operator]
            record = session.get(self.EmployeeProfileRecord, employee_id)
            if record:
                record.profile = profile
                record.source_system = source_system
                record.updated_at = updated_at
            else:
                record = self.EmployeeProfileRecord(
                    employee_id=employee_id,
                    source_system=source_system,
                    profile=profile,
                    updated_at=updated_at,
                )
                session.add(record)
            session.commit()

    def upsert_capacity_allocation(self, allocation: dict[str, Any]) -> None:
        if not self.is_enabled():
            return
        allocation_id = allocation.get("allocation_id")
        if not allocation_id:
            return
        with self.session_factory() as session:  # type: ignore[operator]
            record = session.get(self.CapacityAllocationRecord, allocation_id)
            if record:
                record.employee_id = allocation.get("resource_id", "")
                record.project_id = allocation.get("project_id", "")
                record.start_date = allocation.get("start_date", "")
                record.end_date = allocation.get("end_date", "")
                record.allocation_percentage = float(allocation.get("allocation_percentage", 0))
                record.metadata = allocation
            else:
                record = self.CapacityAllocationRecord(
                    allocation_id=allocation_id,
                    employee_id=allocation.get("resource_id", ""),
                    project_id=allocation.get("project_id", ""),
                    start_date=allocation.get("start_date", ""),
                    end_date=allocation.get("end_date", ""),
                    allocation_percentage=float(allocation.get("allocation_percentage", 0)),
                    source_system=allocation.get("source_system", "agent"),
                    metadata=allocation,
                )
                session.add(record)
            session.commit()

    def list_capacity_allocations(self) -> list[dict[str, Any]]:
        if not self.is_enabled():
            return []
        with self.session_factory() as session:  # type: ignore[operator]
            records = session.scalars(self._select(self.CapacityAllocationRecord)).all()
            return [record.metadata for record in records]

    def upsert_resource_schedule(
        self, resource_id: str, schedule: dict[str, Any], availability: float | None = None
    ) -> None:
        if not self.is_enabled():
            return
        updated_at = datetime.utcnow().isoformat()
        with self.session_factory() as session:  # type: ignore[operator]
            record = session.get(self.ResourceScheduleRecord, resource_id)
            if record:
                record.schedule = schedule
                if availability is not None:
                    record.availability = float(availability)
                record.updated_at = updated_at
            else:
                record = self.ResourceScheduleRecord(
                    resource_id=resource_id,
                    schedule=schedule,
                    availability=float(availability or 0.0),
                    updated_at=updated_at,
                )
                session.add(record)
            session.commit()

    def upsert_forecast(self, forecast_id: str, forecast: dict[str, Any]) -> None:
        if not self.is_enabled():
            return
        forecast_type = forecast.get("type", "capacity")
        created_at = datetime.utcnow().isoformat()
        with self.session_factory() as session:  # type: ignore[operator]
            record = session.get(self.ResourceForecastRecord, forecast_id)
            if record:
                record.payload = forecast
                record.forecast_type = forecast_type
                record.created_at = created_at
            else:
                record = self.ResourceForecastRecord(
                    forecast_id=forecast_id,
                    forecast_type=forecast_type,
                    payload=forecast,
                    created_at=created_at,
                )
                session.add(record)
            session.commit()

    def upsert_performance_score(
        self, resource_id: str, score: float, metadata: dict[str, Any]
    ) -> None:
        if not self.is_enabled():
            return
        updated_at = datetime.utcnow().isoformat()
        with self.session_factory() as session:  # type: ignore[operator]
            record = session.get(self.ResourcePerformanceRecord, resource_id)
            if record:
                record.score = float(score)
                record.metadata = metadata
                record.updated_at = updated_at
            else:
                record = self.ResourcePerformanceRecord(
                    resource_id=resource_id,
                    score=float(score),
                    metadata=metadata,
                    updated_at=updated_at,
                )
                session.add(record)
            session.commit()

    def delete_employee_profile(self, employee_id: str) -> None:
        if not self.is_enabled():
            return
        with self.session_factory() as session:  # type: ignore[operator]
            record = session.get(self.EmployeeProfileRecord, employee_id)
            if record:
                session.delete(record)
                session.commit()

    def close(self) -> None:
        if self.engine:
            self.engine.dispose()


class AzureADClient:
    def __init__(self, client_id: str, tenant_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.client_secret = client_secret
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.scopes = ["https://graph.microsoft.com/.default"]
        from msal import ConfidentialClientApplication

        self.app = ConfidentialClientApplication(
            client_id=client_id, authority=self.authority, client_credential=client_secret
        )

    def _get_token(self) -> str:
        token = self.app.acquire_token_for_client(scopes=self.scopes)
        access_token = token.get("access_token")
        if not access_token:
            raise ValueError(f"Failed to acquire Graph token: {token.get('error_description')}")
        return access_token

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        access_token = self._get_token()
        import requests

        response = requests.get(
            f"https://graph.microsoft.com/v1.0{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def list_users(self) -> list[dict[str, Any]]:
        response = self._request(
            "/users",
            params={"$select": "id,displayName,mail,jobTitle,department,employeeId"},
        )
        return cast(list[dict[str, Any]], response.get("value", []))

    def list_user_skills(self, user_id: str) -> list[str]:
        response = self._request(f"/users/{user_id}/profile/skills")
        return [skill.get("displayName") for skill in response.get("value", []) if skill]

    def get_calendar_availability(
        self, user_id: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        response = self._request(
            f"/users/{user_id}/calendarView",
            params={
                "startDateTime": start.isoformat(),
                "endDateTime": end.isoformat(),
                "$select": "start,end,showAs",
            },
        )
        return cast(list[dict[str, Any]], response.get("value", []))


class EmbeddingClient:
    def __init__(self, endpoint: str | None, api_key: str | None, deployment: str | None) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key and self.deployment)

    def get_embedding(self, text: str) -> list[float]:
        if self.is_configured():
            import requests

            response = requests.post(
                f"{self.endpoint}/openai/deployments/{self.deployment}/embeddings",
                headers={
                    "api-key": cast(str, self.api_key),
                    "Content-Type": "application/json",
                },
                params={"api-version": "2023-05-15"},
                json={"input": text},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return cast(list[float], data["data"][0]["embedding"])
        return self._fallback_embedding(text)

    @staticmethod
    def _fallback_embedding(text: str, dims: int = 64) -> list[float]:
        vector = [0.0] * dims
        for token in text.lower().split():
            token_hash = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            index = token_hash % dims
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class AzureSearchClient:
    def __init__(self, endpoint: str | None, api_key: str | None, index_name: str | None) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.index_name = index_name

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key and self.index_name)

    def upload_documents(self, documents: list[dict[str, Any]]) -> None:
        if not self.is_configured():
            return
        import requests

        response = requests.post(
            f"{self.endpoint}/indexes/{self.index_name}/docs/index",
            headers={"api-key": cast(str, self.api_key), "Content-Type": "application/json"},
            params={"api-version": "2023-07-01-Preview"},
            json={"value": documents},
            timeout=30,
        )
        response.raise_for_status()

    def query_documents(
        self, query_vector: list[float], query_text: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        import requests

        response = requests.post(
            f"{self.endpoint}/indexes/{self.index_name}/docs/search",
            headers={"api-key": cast(str, self.api_key), "Content-Type": "application/json"},
            params={"api-version": "2023-07-01-Preview"},
            json={
                "search": query_text,
                "vectorQueries": [
                    {"vector": query_vector, "fields": "embedding", "k": top_k}
                ],
                "select": "resource_id,skills,role,availability,cost_rate",
            },
            timeout=30,
        )
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json().get("value", []))


class TimeSeriesForecaster:
    def __init__(self, *, automl_endpoint: str | None = None, automl_api_key: str | None = None) -> None:
        self.automl_endpoint = automl_endpoint
        self.automl_api_key = automl_api_key

    def forecast(self, series: list[float], periods: int) -> list[float]:
        if not series:
            return [0.0 for _ in range(periods)]
        automl_forecast = self._forecast_with_automl(series, periods)
        if automl_forecast is not None:
            return automl_forecast
        prophet_forecast = self._forecast_with_prophet(series, periods)
        if prophet_forecast is not None:
            return prophet_forecast
        return self._linear_forecast(series, periods)

    def _linear_forecast(self, series: list[float], periods: int) -> list[float]:
        if len(series) < 2:
            return [series[0] for _ in range(periods)]
        x_values = list(range(len(series)))
        x_mean = sum(x_values) / len(x_values)
        y_mean = sum(series) / len(series)
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, series))
        denominator = sum((x - x_mean) ** 2 for x in x_values) or 1.0
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        start = len(series)
        return [slope * (start + i) + intercept for i in range(periods)]

    def _forecast_with_prophet(self, series: list[float], periods: int) -> list[float] | None:
        try:
            from prophet import Prophet
            import pandas as pd
        except Exception:
            return None
        if len(series) < 2:
            return None
        start_date = datetime.utcnow().date()
        history = [
            {"ds": start_date + timedelta(days=index), "y": value}
            for index, value in enumerate(series)
        ]
        df = pd.DataFrame(history)
        model = Prophet()
        model.fit(df)
        future = model.make_future_dataframe(periods=periods, freq="D")
        forecast = model.predict(future)
        forecast_values = forecast.tail(periods)["yhat"].tolist()
        return [float(value) for value in forecast_values]

    def _forecast_with_automl(self, series: list[float], periods: int) -> list[float] | None:
        if not self.automl_endpoint or not self.automl_api_key:
            return None
        try:
            import requests

            response = requests.post(
                f"{self.automl_endpoint}/forecast",
                headers={
                    "Authorization": f"Bearer {self.automl_api_key}",
                    "Content-Type": "application/json",
                },
                json={"series": series, "horizon": periods},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            forecasts = data.get("forecast")
            if isinstance(forecasts, list):
                return [float(value) for value in forecasts]
        except Exception:
            return None
        return None


class AIMLForecastClient:
    def __init__(self, endpoint: str | None, api_key: str | None) -> None:
        self.endpoint = endpoint
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def train_model(
        self,
        model_name: str,
        series: list[float],
        horizon: int,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        import requests

        response = requests.post(
            f"{self.endpoint}/forecasting/train",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model_name": model_name,
                "series": series,
                "horizon": horizon,
                "metadata": metadata or {},
            },
            timeout=30,
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def forecast(self, model_name: str, series: list[float], horizon: int) -> list[float] | None:
        if not self.is_configured():
            return None
        import requests

        response = requests.post(
            f"{self.endpoint}/forecasting/predict",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model_name": model_name, "series": series, "horizon": horizon},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        forecast = payload.get("forecast")
        if isinstance(forecast, list):
            return [float(value) for value in forecast]
        return None

class EventPublisher:
    def __init__(self, connection_string: str | None, queue_name: str | None) -> None:
        self.connection_string = connection_string
        self.queue_name = queue_name

    def is_configured(self) -> bool:
        return bool(self.connection_string and self.queue_name)

    def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        if not self.is_configured():
            return
        from azure.servicebus import ServiceBusClient, ServiceBusMessage

        with ServiceBusClient.from_connection_string(
            cast(str, self.connection_string)
        ) as client:
            sender = client.get_queue_sender(queue_name=cast(str, self.queue_name))
            with sender:
                message = ServiceBusMessage(json.dumps({"event": event_name, "payload": payload}))
                sender.send_messages(message)


class NotificationService:
    def __init__(
        self,
        graph_client: AzureADClient | None,
        *,
        acs_connection_string: str | None = None,
        acs_sender: str | None = None,
    ) -> None:
        self.graph_client = graph_client
        self.acs_connection_string = acs_connection_string
        self.acs_sender = acs_sender

    def send_email(self, recipient: str, subject: str, content: str) -> None:
        if self.graph_client:
            access_token = self.graph_client._get_token()
            import requests

            response = requests.post(
                "https://graph.microsoft.com/v1.0/users/me/sendMail",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "message": {
                        "subject": subject,
                        "body": {"contentType": "Text", "content": content},
                        "toRecipients": [{"emailAddress": {"address": recipient}}],
                    }
                },
                timeout=30,
            )
            response.raise_for_status()
            return
        if self.acs_connection_string and self.acs_sender:
            try:
                from azure.communication.email import EmailClient
            except Exception as exc:
                raise RuntimeError(
                    "Azure Communication Services email client unavailable."
                ) from exc
            client = EmailClient.from_connection_string(self.acs_connection_string)
            poller = client.begin_send(
                {
                    "senderAddress": self.acs_sender,
                    "recipients": {"to": [{"address": recipient}]},
                    "content": {"subject": subject, "plainText": content},
                }
            )
            poller.result()
            return
        raise RuntimeError("No notification client configured")


class LearningManagementClient:
    def __init__(
        self,
        moodle_endpoint: str | None,
        moodle_token: str | None,
        coursera_endpoint: str | None,
        coursera_token: str | None,
        training_records: list[dict[str, Any]] | None = None,
    ) -> None:
        self.moodle_endpoint = moodle_endpoint
        self.moodle_token = moodle_token
        self.coursera_endpoint = coursera_endpoint
        self.coursera_token = coursera_token
        self.training_records = training_records or []

    def is_configured(self) -> bool:
        return bool(
            self.training_records
            or (self.moodle_endpoint and self.moodle_token)
            or (self.coursera_endpoint and self.coursera_token)
        )

    def fetch_training_records(self, resource_ids: list[str]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if self.training_records:
            record_index = {
                record.get("resource_id"): record for record in self.training_records
            }
            for resource_id in resource_ids:
                if resource_id in record_index:
                    records.append(record_index[resource_id])
            return records
        if self.moodle_endpoint and self.moodle_token:
            records.extend(self._fetch_moodle_records(resource_ids))
        if self.coursera_endpoint and self.coursera_token:
            records.extend(self._fetch_coursera_records(resource_ids))
        return records

    def _fetch_moodle_records(self, resource_ids: list[str]) -> list[dict[str, Any]]:
        import requests

        response = requests.get(
            f"{self.moodle_endpoint}/api/training-records",
            headers={"Authorization": f"Bearer {self.moodle_token}"},
            params={"resource_ids": ",".join(resource_ids)},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return cast(list[dict[str, Any]], payload.get("records", []))

    def _fetch_coursera_records(self, resource_ids: list[str]) -> list[dict[str, Any]]:
        import requests

        response = requests.get(
            f"{self.coursera_endpoint}/api/training-records",
            headers={"Authorization": f"Bearer {self.coursera_token}"},
            params={"resource_ids": ",".join(resource_ids)},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return cast(list[dict[str, Any]], payload.get("records", []))


class ApprovalWorkflowClient:
    def __init__(self, approval_agent: Any | None, event_bus: Any | None) -> None:
        self.approval_agent = approval_agent
        self.event_bus = event_bus

    async def request_approval(
        self,
        request: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        approver_hint: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "request_type": "resource_change",
            "request_id": request.get("request_id"),
            "requester": request.get("requested_by", "unknown"),
            "details": {
                "project_id": request.get("project_id"),
                "required_skills": request.get("required_skills", []),
                "start_date": request.get("start_date"),
                "end_date": request.get("end_date"),
                "effort": request.get("effort", 1.0),
                "approver_hint": approver_hint,
            },
            "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
        }
        if self.approval_agent:
            return await self.approval_agent.process(payload)
        if self.event_bus:
            await self.event_bus.publish("approval.requested", payload)
        return {"status": "pending", "approval_id": None, "approvers": []}

    async def record_decision(
        self,
        approval_id: str,
        *,
        decision: str,
        approver_id: str,
        comments: str | None,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        payload = {
            "approval_id": approval_id,
            "decision": decision,
            "approver_id": approver_id,
            "comments": comments,
            "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
        }
        if self.approval_agent:
            return await self.approval_agent.process(payload)
        if self.event_bus:
            await self.event_bus.publish("approval.decision", payload)
        return {"status": decision}


class SimpleAnalyticsClient:
    def __init__(self) -> None:
        self.metrics: list[tuple[str, float, dict[str, Any]]] = []

    def record_metric(self, name: str, value: float, metadata: dict[str, Any] | None = None) -> None:
        self.metrics.append((name, value, metadata or {}))


class ResourceCapacityAgent(BaseAgent):
    """
    Resource & Capacity Management Agent - Manages resource pool, capacity planning, and allocation.

    Key Capabilities:
    - Centralized resource pool management
    - Demand intake and approval routing
    - Skill matching and intelligent search
    - Capacity planning and forecasting
    - Scenario modeling and what-if analysis
    - Role-based vs named assignments
    - Cross-project resource management
    - HR and timesheet system integration
    - Alerts and notifications for over-allocation
    """

    def __init__(
        self,
        agent_id: str = "resource-capacity-management",
        config: dict[str, Any] | None = None,
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.max_allocation_threshold = (
            config.get("max_allocation_threshold", 1.0) if config else 1.0
        )
        self.skill_matching_threshold = (
            config.get("skill_matching_threshold", 0.70) if config else 0.70
        )
        self.forecast_horizon_months = config.get("forecast_horizon_months", 12) if config else 12
        self.utilization_target = config.get("utilization_target", 0.85) if config else 0.85
        self.scenario_engine = ScenarioEngine()
        self.skill_match_weights = (
            config.get(
                "skill_match_weights",
                {"skills": 0.6, "availability": 0.2, "cost": 0.1, "performance": 0.1},
            )
            if config
            else {"skills": 0.6, "availability": 0.2, "cost": 0.1, "performance": 0.1}
        )
        self.default_working_hours_per_day = (
            config.get("working_hours_per_day", 8) if config else 8
        )
        self.default_working_days = (
            config.get("working_days", [0, 1, 2, 3, 4]) if config else [0, 1, 2, 3, 4]
        )
        self.max_concurrent_allocations = (
            config.get("max_concurrent_allocations", 3) if config else 3
        )
        self.enforce_allocation_constraints = (
            config.get("enforce_allocation_constraints", True) if config else True
        )

        resource_store_path = (
            Path(config.get("resource_store_path", "data/resource_pool.json"))
            if config
            else Path("data/resource_pool.json")
        )
        allocation_store_path = (
            Path(config.get("allocation_store_path", "data/resource_allocations.json"))
            if config
            else Path("data/resource_allocations.json")
        )
        calendar_store_path = (
            Path(config.get("calendar_store_path", "data/resource_calendars.json"))
            if config
            else Path("data/resource_calendars.json")
        )
        self.resource_store = TenantStateStore(resource_store_path)
        self.allocation_store = TenantStateStore(allocation_store_path)
        self.calendar_store = TenantStateStore(calendar_store_path)

        # Data stores (will be replaced with database connections)
        self.resource_pool: dict[str, Any] = {}
        self.capacity_calendar: dict[str, Any] = {}
        self.allocations: dict[str, Any] = {}
        self.demand_requests: dict[str, Any] = {}
        self.utilization_metrics: dict[str, Any] = {}
        self.training_records: dict[str, dict[str, Any]] = {}
        self.performance_scores: dict[str, float] = {}
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()
        self.db_service: DatabaseStorageService | None = None
        self.forecasting_model: ForecastingModel | None = None
        self.ml_forecast_client = config.get("ml_forecast_client") if config else None
        if self.ml_forecast_client is None:
            self.ml_forecast_client = AIMLForecastClient(
                os.getenv("AZURE_ML_ENDPOINT"),
                os.getenv("AZURE_ML_API_KEY"),
            )
        self.repository = ResourceCapacityRepository(os.getenv("RESOURCE_CAPACITY_DATABASE_URL"))
        self.graph_client: AzureADClient | None = None
        self.calendar_service = CalendarIntegrationService(
            (config or {}).get("calendar") if config else None
        )
        self.embedding_client: EmbeddingClient | None = None
        self.search_client: AzureSearchClient | None = None
        self.event_publisher = EventPublisher(
            os.getenv("AZURE_SERVICEBUS_CONNECTION_STRING"),
            os.getenv("AZURE_SERVICEBUS_QUEUE_NAME"),
        )
        self.notification_service: NotificationService | None = None
        self.redis_client: Any | None = None
        self._skills_indexed = False
        self.analytics_client = config.get("analytics_client") if config else None
        if self.analytics_client is None:
            if importlib.util.find_spec("pydantic_settings") is None:
                self.analytics_client = SimpleAnalyticsClient()
            else:
                from services.integration.analytics import AnalyticsClient

                self.analytics_client = AnalyticsClient()
        self.org_structure = config.get("org_structure", {}) if config else {}
        self.approval_routing = config.get("approval_routing", {}) if config else {}
        self.default_tenant_id = config.get("default_tenant_id", "system") if config else "system"
        training_records = config.get("training_records") if config else None
        self.training_client = config.get("training_client") if config else None
        if self.training_client is None:
            self.training_client = LearningManagementClient(
                os.getenv("MOODLE_LMS_ENDPOINT"),
                os.getenv("MOODLE_LMS_TOKEN"),
                os.getenv("COURSERA_BUSINESS_ENDPOINT"),
                os.getenv("COURSERA_BUSINESS_TOKEN"),
                training_records=training_records,
            )
        approval_agent = config.get("approval_agent") if config else None
        self.approval_client = config.get("approval_client") if config else None
        if self.approval_client is None:
            self.approval_client = ApprovalWorkflowClient(approval_agent, self.event_bus)
        self.attrition_rate = float(config.get("attrition_rate", 0.0) if config else 0.0)
        self.seasonality_factors = config.get("seasonality_factors", {}) if config else {}
        self.training_capacity_impact = float(
            config.get("training_capacity_impact", 0.1) if config else 0.1
        )
        self.skill_development_uplift = float(
            config.get("skill_development_uplift", 0.05) if config else 0.05
        )
        self.hr_profile_provider = config.get("hr_profile_provider") if config else None

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Resource & Capacity Management Agent...")

        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.logger.info("Database Storage Service initialized")

        self.forecasting_model = ForecastingModel()
        self.logger.info("Forecasting model initialized")

        azure_client_id = os.getenv("AZURE_CLIENT_ID")
        azure_tenant_id = os.getenv("AZURE_TENANT_ID")
        azure_client_secret = os.getenv("AZURE_CLIENT_SECRET")
        if azure_client_id and azure_tenant_id and azure_client_secret:
            self.graph_client = AzureADClient(
                azure_client_id, azure_tenant_id, azure_client_secret
            )
        self.embedding_client = EmbeddingClient(
            os.getenv("AZURE_OPENAI_ENDPOINT"),
            os.getenv("AZURE_OPENAI_API_KEY"),
            os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        )
        self.search_client = AzureSearchClient(
            os.getenv("AZURE_SEARCH_ENDPOINT"),
            os.getenv("AZURE_SEARCH_API_KEY"),
            os.getenv("AZURE_SEARCH_INDEX"),
        )
        self.notification_service = NotificationService(
            self.graph_client,
            acs_connection_string=os.getenv("AZURE_COMMUNICATION_SERVICE_CONNECTION_STRING"),
            acs_sender=os.getenv("AZURE_COMMUNICATION_EMAIL_SENDER"),
        )
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            from redis import Redis

            self.redis_client = Redis.from_url(redis_url, decode_responses=True)

        await self._sync_hr_systems()
        await self._sync_training_records()
        await self._refresh_capacity_allocations()

        self.logger.info(
            "Using local calendar storage for working hours and leave tracking"
        )

        self.logger.info("Resource & Capacity Management Agent initialized")
        self._subscribe_to_events()

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "add_resource",
            "update_resource",
            "delete_resource",
            "request_resource",
            "approve_request",
            "search_resources",
            "match_skills",
            "forecast_capacity",
            "plan_capacity",
            "scenario_analysis",
            "allocate_resource",
            "get_availability",
            "get_utilization",
            "identify_conflicts",
            "get_resource_pool",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "add_resource":
            resource_data = input_data.get("resource", {})
            required_fields = ["resource_id", "name", "role"]
            for field in required_fields:
                if field not in resource_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False
        elif action == "update_resource":
            resource_data = input_data.get("resource", {})
            if "resource_id" not in resource_data:
                self.logger.warning("Missing required field: resource_id")
                return False

        elif action == "delete_resource":
            resource_id = input_data.get("resource_id")
            if not resource_id:
                self.logger.warning("Missing required field: resource_id")
                return False

        elif action == "request_resource":
            request_data = input_data.get("request", {})
            required_fields = ["project_id", "required_skills", "start_date", "end_date"]
            for field in required_fields:
                if field not in request_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process resource and capacity management requests.

        Args:
            input_data: {
                "action": "add_resource" | "request_resource" | "approve_request" |
                          "search_resources" | "match_skills" | "forecast_capacity" |
                          "plan_capacity" | "scenario_analysis" | "allocate_resource" |
                          "get_availability" | "get_utilization" | "identify_conflicts" |
                          "get_resource_pool",
                "resource": Resource profile data,
                "request": Resource request data,
                "request_id": Request ID for approval,
                "search_criteria": Search criteria,
                "skills_required": Required skills for matching,
                "scenario_params": Scenario parameters,
                "allocation": Allocation details,
                "resource_id": Resource ID,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - add_resource: Resource ID, profile
            - request_resource: Request ID, recommended resources
            - approve_request: Approval status, allocated resource
            - search_resources: Matching resources with availability
            - match_skills: Ranked candidates with skill match scores
            - forecast_capacity: Capacity vs demand forecast
            - plan_capacity: Capacity plan with recommendations
            - scenario_analysis: Scenario comparison metrics
            - allocate_resource: Allocation ID, updated capacity
            - get_availability: Resource availability calendar
            - get_utilization: Utilization metrics and trends
            - identify_conflicts: Resource conflicts and recommendations
            - get_resource_pool: Complete resource pool data
        """
        action = input_data.get("action", "add_resource")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        if action == "add_resource":
            return await self._add_resource(input_data.get("resource", {}), tenant_id=tenant_id)

        elif action == "update_resource":
            return await self._update_resource(
                input_data.get("resource", {}), tenant_id=tenant_id
            )

        elif action == "delete_resource":
            resource_id = input_data.get("resource_id")
            assert isinstance(resource_id, str), "resource_id must be a string"
            return await self._delete_resource(resource_id, tenant_id=tenant_id)

        elif action == "request_resource":
            return await self._request_resource(input_data.get("request", {}), tenant_id=tenant_id)

        elif action == "approve_request":
            request_id = input_data.get("request_id")
            assert isinstance(request_id, str), "request_id must be a string"
            return await self._approve_request(
                request_id, input_data.get("approval_decision", {}), tenant_id=tenant_id
            )

        elif action == "search_resources":
            return await self._search_resources(input_data.get("search_criteria", {}))

        elif action == "match_skills":
            return await self._match_skills(
                input_data.get("skills_required", []), input_data.get("project_context", {})
            )

        elif action == "forecast_capacity":
            return await self._forecast_capacity(input_data.get("filters", {}))

        elif action == "plan_capacity":
            return await self._plan_capacity(input_data.get("planning_horizon", {}))

        elif action == "scenario_analysis":
            return await self._scenario_analysis(input_data.get("scenario_params", {}))

        elif action == "allocate_resource":
            return await self._allocate_resource(
                input_data.get("allocation", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "get_availability":
            resource_id = input_data.get("resource_id")
            assert isinstance(resource_id, str), "resource_id must be a string"
            return await self._get_availability(
                resource_id, input_data.get("date_range", {}), tenant_id=tenant_id
            )

        elif action == "get_utilization":
            return await self._get_utilization(input_data.get("filters", {}))

        elif action == "identify_conflicts":
            return await self._identify_conflicts(input_data.get("filters", {}))

        elif action == "get_resource_pool":
            return await self._get_resource_pool(input_data.get("filters", {}), tenant_id=tenant_id)

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _add_resource(
        self, resource_data: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Add a resource to the pool.

        Returns resource ID and profile.
        """
        self.logger.info("Adding resource to pool")

        resource_id = resource_data.get("resource_id")
        assert isinstance(resource_id, str), "resource_id must be a string"
        name = resource_data.get("name")
        role = resource_data.get("role")
        skills = resource_data.get("skills", [])
        location = resource_data.get("location", "Unknown")
        cost_rate = resource_data.get("cost_rate", 0.0)
        certifications = resource_data.get("certifications", [])
        training_record = resource_data.get("training_record")
        training_metadata = {}

        # Create resource profile
        resource_profile = {
            "resource_id": resource_id,
            "name": name,
            "role": role,
            "skills": skills,
            "location": location,
            "cost_rate": cost_rate,
            "certifications": certifications,
            "availability": 1.0,  # 100% available by default
            "team_memberships": resource_data.get("team_memberships", []),
            "created_at": datetime.utcnow().isoformat(),
            "status": "Active",
            "training": training_metadata,
            "training_load": 0.0,
        }

        self.resource_pool[resource_id] = resource_profile
        if training_record:
            training_metadata = await self._apply_training_record(resource_id, training_record)
            resource_profile["training"] = training_metadata
            resource_profile["training_load"] = training_metadata.get("training_load", 0.0)

        # Initialize capacity calendar
        calendar_entry = {
            "resource_id": resource_id,
            "available_hours_per_day": resource_data.get(
                "available_hours_per_day", self.default_working_hours_per_day
            ),
            "working_days": resource_data.get("working_days", self.default_working_days),
            "planned_leave": resource_data.get("planned_leave", []),
            "holidays": resource_data.get("holidays", []),
        }
        self.capacity_calendar[resource_id] = calendar_entry
        self.calendar_store.upsert(tenant_id, resource_id, calendar_entry)
        await self._persist_resource_schedule(
            resource_id,
            calendar_entry,
            tenant_id=tenant_id,
            availability=resource_profile.get("availability", 1.0),
        )

        validation = await self._validate_resource_record(resource_profile, tenant_id=tenant_id)

        # Store resource
        self.resource_pool[resource_id] = resource_profile
        self.resource_store.upsert(tenant_id, resource_id, resource_profile)
        canonical_profile = dict(resource_profile)
        canonical_profile.update(
            {
                "employee_id": resource_id,
                "source_system": "agent",
            }
        )
        await self._store_canonical_profile(resource_id, canonical_profile, resource_profile)
        await self._index_skills()
        await self._publish_resource_event("resource.added", resource_profile)

        self.logger.info(f"Added resource: {resource_id}")

        return {
            "resource_id": resource_id,
            "profile": resource_profile,
            "status": "Active",
            "data_quality": validation,
        }

    async def _update_resource(
        self, resource_data: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """Update resource details in the pool."""
        resource_id = resource_data.get("resource_id")
        assert isinstance(resource_id, str), "resource_id must be a string"
        existing = self.resource_pool.get(resource_id)
        if not existing:
            return await self._add_resource(resource_data, tenant_id=tenant_id)

        updated = {**existing, **{k: v for k, v in resource_data.items() if v is not None}}
        updated["updated_at"] = datetime.utcnow().isoformat()
        self.resource_pool[resource_id] = updated
        self.resource_store.upsert(tenant_id, resource_id, updated)
        canonical_profile = dict(updated)
        canonical_profile.update({"employee_id": resource_id, "source_system": "agent"})
        await self._store_canonical_profile(resource_id, canonical_profile, updated)
        await self._index_skills()
        await self._publish_resource_event("resource.updated", updated)
        return {"resource_id": resource_id, "profile": updated, "status": updated.get("status")}

    async def _delete_resource(self, resource_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Delete (deactivate) a resource from the pool."""
        if resource_id not in self.resource_pool:
            return {"resource_id": resource_id, "status": "NotFound"}
        await self._deactivate_resource(resource_id, reason="manual_delete")
        if self.db_service:
            await self.db_service.delete("resource_profiles", resource_id)
        self.repository.delete_employee_profile(resource_id)
        return {"resource_id": resource_id, "status": "Inactive"}

    async def _persist_resource_schedule(
        self,
        resource_id: str,
        schedule: dict[str, Any],
        *,
        tenant_id: str,
        availability: float | None = None,
    ) -> None:
        self.repository.upsert_resource_schedule(resource_id, schedule, availability)
        if self.db_service:
            await self.db_service.store(
                "resource_schedules",
                resource_id,
                {
                    "resource_id": resource_id,
                    "schedule": schedule,
                    "availability": availability,
                    "tenant_id": tenant_id,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
        if self.redis_client:
            self.redis_client.set(
                f"resource_schedule:{resource_id}", json.dumps(schedule), ex=3600
            )

    async def _request_resource(
        self, request_data: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Submit a resource request.

        Returns request ID and recommended resources.
        """
        self.logger.info("Processing resource request")

        # Generate unique request ID
        request_id = await self._generate_request_id()

        project_id = request_data.get("project_id")
        required_skills = request_data.get("required_skills", [])
        start_date = request_data.get("start_date")
        end_date = request_data.get("end_date")
        effort = request_data.get("effort", 1.0)  # FTE

        assert isinstance(start_date, str), "start_date must be a string"
        assert isinstance(end_date, str), "end_date must be a string"

        # Match skills and find candidates
        candidates = await self._match_skills(required_skills, {"project_id": project_id})

        # Check availability for each candidate
        available_candidates = []
        for candidate in candidates.get("candidates", []):
            availability = await self._check_availability(
                candidate["resource_id"], start_date, end_date, effort
            )

            if availability.get("is_available"):
                candidate["availability_windows"] = availability.get("windows", [])
                available_candidates.append(candidate)

        # Create request record
        request = {
            "request_id": request_id,
            "project_id": project_id,
            "project_role": request_data.get("project_role"),
            "project_roles": request_data.get("project_roles", []),
            "required_skills": required_skills,
            "start_date": start_date,
            "end_date": end_date,
            "effort": effort,
            "requested_by": request_data.get("requested_by", "unknown"),
            "requested_at": datetime.utcnow().isoformat(),
            "status": "Pending",
            "recommended_candidates": available_candidates,
        }

        # Store request
        self.demand_requests[request_id] = request

        # Route to approver
        approver = await self._determine_approver(request)
        approval_payload = {}
        if self.approval_client:
            approval_payload = await self.approval_client.request_approval(
                request,
                tenant_id=tenant_id,
                correlation_id=request_id,
                approver_hint=approver,
            )
            request["approval_id"] = approval_payload.get("approval_id")
            request["approval_status"] = approval_payload.get("status")

        if self.db_service:
            await self.db_service.store("resource_requests", request_id, request)
        await self._publish_resource_event("resource.request.created", request)
        await self._notify_requester(request)

        self.logger.info(f"Created resource request: {request_id}")

        return {
            "request_id": request_id,
            "status": "Pending",
            "recommended_candidates": available_candidates,
            "approver": approver,
            "approval": approval_payload,
            "next_steps": f"Request routed to {approver} for approval",
        }

    async def _approve_request(
        self,
        request_id: str,
        approval_decision: dict[str, Any],
        *,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Approve or reject a resource request.

        Returns approval status and allocation if approved.
        """
        self.logger.info(f"Processing approval for request: {request_id}")

        request = self.demand_requests.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        approved = approval_decision.get("approved", False)
        selected_resource = approval_decision.get("selected_resource_id")
        comments = approval_decision.get("comments", "")
        approver_id = approval_decision.get("approver_id", "unknown")
        approval_id = request.get("approval_id")
        if approval_id and self.approval_client:
            await self.approval_client.record_decision(
                approval_id,
                decision="approved" if approved else "rejected",
                approver_id=approver_id,
                comments=comments,
                tenant_id=tenant_id,
                correlation_id=request_id,
            )

        if approved and selected_resource:
            # Create allocation
            allocation = await self._allocate_resource(
                {
                    "resource_id": selected_resource,
                    "project_id": request.get("project_id"),
                    "start_date": request.get("start_date"),
                    "end_date": request.get("end_date"),
                    "allocation_percentage": request.get("effort", 1.0) * 100,
                }
            )

            request["status"] = "Approved"
            request["approved_at"] = datetime.utcnow().isoformat()
            request["allocated_resource"] = selected_resource
            request["allocation_id"] = allocation.get("allocation_id")

            # Notify Schedule & Planning Agent
            # Future work: Integrate with Agent 10
            await self._publish_resource_event("resource.request.approved", request)
            await self._notify_requester(request)
            await self._notify_project_manager(request)

            return {
                "request_id": request_id,
                "status": "Approved",
                "allocation": allocation,
                "comments": comments,
            }
        else:
            request["status"] = "Rejected"
            request["rejected_at"] = datetime.utcnow().isoformat()
            request["rejection_reason"] = comments

            # Future work: Notify requester
            await self._publish_resource_event("resource.request.rejected", request)
            await self._notify_requester(request)

            return {"request_id": request_id, "status": "Rejected", "rejection_reason": comments}

    async def _search_resources(self, search_criteria: dict[str, Any]) -> dict[str, Any]:
        """
        Search for resources by criteria.

        Returns matching resources.
        """
        self.logger.info("Searching for resources")

        role = search_criteria.get("role")
        location = search_criteria.get("location")
        skills = search_criteria.get("skills", [])
        availability_required = search_criteria.get("availability_required")

        matching_resources = []

        for resource_id, resource in self.resource_pool.items():
            # Check role
            if role and resource.get("role") != role:
                continue

            # Check location
            if location and resource.get("location") != location:
                continue

            # Check skills
            if skills:
                resource_skills = set(self._get_effective_skills(resource))
                required_skills = set(skills)
                if not required_skills.issubset(resource_skills):
                    continue

            # Check availability if required
            if availability_required:
                if resource.get("availability", 0) < availability_required:
                    continue

            matching_resources.append(resource)

        return {
            "total_matches": len(matching_resources),
            "resources": matching_resources,
            "search_criteria": search_criteria,
        }

    async def _find_matching_resources(
        self, skills_required: list[str], *, availability_floor: float = 0.0
    ) -> list[dict[str, Any]]:
        """Find matching resources using weighted scoring."""
        required_skills = {skill.lower() for skill in skills_required if skill}
        max_cost = max(
            (float(resource.get("cost_rate", 0)) for resource in self.resource_pool.values()),
            default=0.0,
        )
        weights = {
            "skills": float(self.skill_match_weights.get("skills", 0.7)),
            "availability": float(self.skill_match_weights.get("availability", 0.2)),
            "cost": float(self.skill_match_weights.get("cost", 0.1)),
            "performance": float(self.skill_match_weights.get("performance", 0.1)),
        }
        total_weight = sum(weights.values()) or 1.0
        normalized_weights = {key: value / total_weight for key, value in weights.items()}

        matches: list[dict[str, Any]] = []
        for resource_id, resource in self.resource_pool.items():
            resource_skills = {
                skill.lower() for skill in self._get_effective_skills(resource) if skill
            }
            skill_score = (
                len(resource_skills.intersection(required_skills)) / len(required_skills)
                if required_skills
                else 1.0
            )
            availability_score = float(resource.get("availability", 0.0))
            if availability_score < availability_floor:
                continue
            cost_rate = float(resource.get("cost_rate", 0.0))
            cost_score = 1.0 - (cost_rate / max_cost) if max_cost else 1.0
            performance_score = await self._get_performance_score(resource_id, {})

            weighted_score = (
                normalized_weights["skills"] * skill_score
                + normalized_weights["availability"] * availability_score
                + normalized_weights["cost"] * cost_score
                + normalized_weights["performance"] * performance_score
            )
            matches.append(
                {
                    "resource_id": resource_id,
                    "resource_name": resource.get("name"),
                    "role": resource.get("role"),
                    "skills": list(resource_skills),
                    "match_score": skill_score,
                    "availability_score": availability_score,
                    "cost_score": cost_score,
                    "performance_score": performance_score,
                    "weighted_score": weighted_score,
                }
            )

        matches.sort(key=lambda item: item["weighted_score"], reverse=True)
        return matches

    async def _match_skills(
        self, skills_required: list[str], project_context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Match resources to required skills using AI.

        Returns ranked candidates with skill match scores.
        """
        self.logger.info("Matching skills to resources")

        candidates = []
        query_text = " ".join(skills_required)
        embedding_client = self.embedding_client or EmbeddingClient(None, None, None)
        query_embedding = embedding_client.get_embedding(query_text)
        search_candidates = []
        if self.search_client and self.search_client.is_configured():
            if not self._skills_indexed:
                await self._index_skills()
            search_candidates = self.search_client.query_documents(
                query_embedding, query_text=query_text, top_k=10
            )
        if search_candidates:
            for result in search_candidates:
                resource_id = result.get("resource_id")
                resource = self.resource_pool.get(resource_id, {})
                if not resource_id:
                    continue
                performance_score = await self._get_performance_score(
                    resource_id, project_context
                )
                semantic_score = float(result.get("@search.score", 0.0))
                combined_score = (semantic_score * 0.6) + (performance_score * 0.4)
                if combined_score >= self.skill_matching_threshold:
                    candidates.append(
                        {
                            "resource_id": resource_id,
                            "resource_name": resource.get("name"),
                            "role": resource.get("role"),
                            "skills": self._get_effective_skills(resource),
                            "match_score": semantic_score,
                            "weighted_score": semantic_score,
                            "availability_score": resource.get("availability", 0.0),
                            "cost_score": resource.get("cost_rate", 0.0),
                            "performance_score": performance_score,
                            "combined_score": combined_score,
                            "cost_rate": resource.get("cost_rate"),
                        }
                    )
        else:
            matches = await self._find_matching_resources(skills_required)
            for match in matches:
                resource_id = match["resource_id"]
                resource_skills = " ".join(match.get("skills", []))
                resource_embedding = embedding_client.get_embedding(resource_skills)
                semantic_similarity = self._cosine_similarity(
                    query_embedding, resource_embedding
                )
                performance_score = await self._get_performance_score(
                    resource_id, project_context
                )
                combined_score = (
                    match["weighted_score"] * 0.5
                    + semantic_similarity * 0.3
                    + performance_score * 0.2
                )

                if combined_score >= self.skill_matching_threshold:
                    candidates.append(
                        {
                            "resource_id": resource_id,
                            "resource_name": match.get("resource_name"),
                            "role": match.get("role"),
                            "skills": match.get("skills", []),
                            "match_score": semantic_similarity,
                            "weighted_score": match.get("weighted_score"),
                            "availability_score": match.get("availability_score"),
                            "cost_score": match.get("cost_score"),
                            "performance_score": performance_score,
                            "combined_score": combined_score,
                            "cost_rate": self.resource_pool.get(resource_id, {}).get("cost_rate"),
                        }
                    )

        candidates.sort(key=lambda x: x["combined_score"], reverse=True)

        return {
            "skills_required": skills_required,
            "candidates": candidates,
            "total_candidates": len(candidates),
        }

    async def _forecast_capacity(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Forecast future capacity vs demand.

        Returns capacity forecast with bottlenecks.
        """
        self.logger.info("Forecasting capacity")

        history_months = int(filters.get("history_months", 6))
        tenant_id = filters.get("tenant_id") or self.default_tenant_id
        cache_key = (
            f"capacity_forecast:{tenant_id}:{history_months}:{self.forecast_horizon_months}"
        )
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                try:
                    return cast(dict[str, Any], json.loads(cached))
                except json.JSONDecodeError:
                    pass

        # Calculate current capacity
        current_capacity = await self._calculate_total_capacity()

        # Get current demand
        current_demand = await self._calculate_total_demand()

        capacity_series, demand_series = await self._build_capacity_demand_history(history_months)
        ml_metadata = await self._train_forecasting_models(
            capacity_series, demand_series, tenant_id=tenant_id, history_months=history_months
        )
        capacity_forecast = None
        demand_forecast = None
        if self.ml_forecast_client and self.ml_forecast_client.is_configured():
            capacity_forecast = self.ml_forecast_client.forecast(
                f"{tenant_id}-capacity", capacity_series, self.forecast_horizon_months
            )
            demand_forecast = self.ml_forecast_client.forecast(
                f"{tenant_id}-demand", demand_series, self.forecast_horizon_months
            )
        if capacity_forecast is None or demand_forecast is None:
            forecaster = TimeSeriesForecaster(
                automl_endpoint=os.getenv("AZURE_AUTOML_ENDPOINT"),
                automl_api_key=os.getenv("AZURE_AUTOML_API_KEY"),
            )
            capacity_forecast = forecaster.forecast(
                capacity_series, self.forecast_horizon_months
            )
            demand_forecast = forecaster.forecast(demand_series, self.forecast_horizon_months)
        future_capacity = self._adjust_capacity_forecast(capacity_forecast)
        future_demand = self._adjust_demand_forecast(demand_forecast)

        # Identify bottlenecks
        bottlenecks = await self._identify_capacity_bottlenecks(future_capacity, future_demand)

        # Generate recommendations
        recommendations = await self._generate_capacity_recommendations(bottlenecks)
        assumptions = {
            "attrition_rate": self._get_attrition_rate(),
            "seasonality_factors": self.seasonality_factors,
            "training_capacity_impact": self.training_capacity_impact,
            "skill_development_uplift": self.skill_development_uplift,
            "ml_metadata": ml_metadata,
        }
        forecast_payload = {
            "forecast_horizon_months": self.forecast_horizon_months,
            "current_capacity": current_capacity,
            "current_demand": current_demand,
            "current_utilization": current_demand / current_capacity if current_capacity > 0 else 0,
            "history": {
                "months": history_months,
                "capacity_series": capacity_series,
                "demand_series": demand_series,
            },
            "future_capacity": future_capacity,
            "future_demand": future_demand,
            "bottlenecks": bottlenecks,
            "recommendations": recommendations,
            "assumptions": assumptions,
            "type": "capacity_vs_demand",
        }
        forecast_id = f"forecast-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        if self.db_service:
            await self.db_service.store(
                "capacity_forecasts",
                forecast_id,
                {
                    "created_at": datetime.utcnow().isoformat(),
                    "forecast": forecast_payload,
                    "assumptions": assumptions,
                },
            )
        self.repository.upsert_forecast(forecast_id, forecast_payload)
        await self._publish_resource_event("resource.capacity.forecasted", forecast_payload)
        if self.redis_client:
            self.redis_client.set(cache_key, json.dumps(forecast_payload), ex=900)
        if self.analytics_client:
            self.analytics_client.record_metric("capacity.current", current_capacity)
            self.analytics_client.record_metric("demand.current", current_demand)
            self.analytics_client.record_metric(
                "utilization.current",
                current_demand / current_capacity if current_capacity else 0.0,
            )

        return forecast_payload

    async def _plan_capacity(self, planning_horizon: dict[str, Any]) -> dict[str, Any]:
        """
        Create capacity plan.

        Returns capacity plan with allocation strategy.
        """
        self.logger.info("Planning capacity")

        # Get forecast
        forecast = await self._forecast_capacity({})

        # Identify gaps
        gaps = await self._identify_capacity_gaps(forecast)

        # Generate mitigation strategies
        strategies = await self._generate_mitigation_strategies(gaps)
        optimization = await self._optimize_resource_allocations(planning_horizon)

        # Create capacity plan
        plan = {
            "planning_horizon": planning_horizon,
            "forecast": forecast,
            "gaps": gaps,
            "mitigation_strategies": strategies,
            "optimization": optimization,
            "hiring_recommendations": await self._generate_hiring_recommendations(gaps),
            "training_recommendations": await self._generate_training_recommendations(gaps),
            "created_at": datetime.utcnow().isoformat(),
        }

        return plan

    async def _scenario_analysis(self, scenario_params: dict[str, Any]) -> dict[str, Any]:
        """
        Perform what-if scenario analysis.

        Returns scenario comparison metrics.
        """
        self.logger.info("Running scenario analysis")

        scenario_name = scenario_params.get("scenario_name", "Unnamed Scenario")
        changes = scenario_params.get("changes", {})

        baseline = await self._create_baseline_scenario()
        scenario_output = await self.scenario_engine.run_scenario(
            baseline=baseline,
            scenario_params=changes,
            scenario_builder=self._apply_scenario_changes,
            metrics_builder=self._calculate_scenario_metrics,
            comparison_builder=self._compare_scenarios,
            recommendation_builder=self._generate_scenario_recommendation,
        )

        return {
            "scenario_name": scenario_name,
            "scenario_params": scenario_params,
            "baseline_metrics": scenario_output["baseline_metrics"],
            "scenario_metrics": scenario_output["scenario_metrics"],
            "comparison": scenario_output["comparison"],
            "recommendation": scenario_output.get("recommendation"),
        }

    async def _allocate_resource(
        self, allocation_data: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """
        Allocate a resource to a project/task.

        Returns allocation ID and updated capacity.
        """
        self.logger.info("Allocating resource")

        # Generate unique allocation ID
        allocation_id = await self._generate_allocation_id()

        resource_id = allocation_data.get("resource_id")
        project_id = allocation_data.get("project_id")
        start_date = allocation_data.get("start_date")
        end_date = allocation_data.get("end_date")
        allocation_percentage = allocation_data.get("allocation_percentage", 100)

        assert isinstance(resource_id, str), "resource_id must be a string"
        assert isinstance(start_date, str), "start_date must be a string"
        assert isinstance(end_date, str), "end_date must be a string"

        lock_key = f"resource_allocation_lock:{resource_id}"
        lock_acquired = await self._acquire_lock(lock_key, ttl_seconds=15)
        if not lock_acquired:
            raise RuntimeError("Allocation is already being processed for this resource.")

        try:
            validation = await self._validate_allocation(
                resource_id, start_date, end_date, allocation_percentage
            )

            if not validation.get("valid"):
                raise ValueError(f"Invalid allocation: {validation.get('reason')}")

            allocation = {
                "allocation_id": allocation_id,
                "resource_id": resource_id,
                "project_id": project_id,
                "start_date": start_date,
                "end_date": end_date,
                "allocation_percentage": allocation_percentage,
                "status": "Active",
                "created_at": datetime.utcnow().isoformat(),
            }

            if resource_id not in self.allocations:
                self.allocations[resource_id] = []
            self.allocations[resource_id].append(allocation)
            self.allocation_store.upsert(tenant_id, allocation_id, allocation)
            self.repository.upsert_capacity_allocation(allocation)
            if self.redis_client:
                self.redis_client.set(
                    f"allocation:{allocation_id}", json.dumps(allocation), ex=3600
                )
                self.redis_client.rpush(
                    f"resource_allocations:{resource_id}", json.dumps(allocation)
                )

            await self._update_resource_availability(resource_id)

            await self._publish_allocation_event(
                allocation, tenant_id=tenant_id, correlation_id=correlation_id
            )
            await self._publish_resource_event("resource.allocation.created", allocation)

            self.logger.info(f"Created allocation: {allocation_id}")

            return allocation
        finally:
            await self._release_lock(lock_key)

    async def _get_availability(
        self, resource_id: str, date_range: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Get resource availability for a date range.

        Returns availability calendar.
        """
        self.logger.info(f"Getting availability for resource: {resource_id}")

        resource = self.resource_pool.get(resource_id)
        if not resource:
            resource = self.resource_store.get(tenant_id, resource_id)
            if resource:
                self.resource_pool[resource_id] = resource
        if not resource:
            raise ValueError(f"Resource not found: {resource_id}")

        calendar = self.capacity_calendar.get(resource_id, {})
        if not calendar:
            calendar = self.calendar_store.get(tenant_id, resource_id) or {}
            if calendar:
                self.capacity_calendar[resource_id] = calendar
        allocations = self._load_allocations(resource_id)

        start_date_str = date_range.get("start_date")
        end_date_str = date_range.get("end_date")
        assert isinstance(start_date_str, str), "start_date must be a string"
        assert isinstance(end_date_str, str), "end_date must be a string"
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)

        # Calculate availability for each day in range
        availability_by_day = []
        current_date = start_date

        while current_date <= end_date:
            day_availability = await self._calculate_day_availability(
                resource_id, current_date, calendar, allocations
            )

            availability_by_day.append(day_availability)
            current_date += timedelta(days=1)

        return {
            "resource_id": resource_id,
            "resource_name": resource.get("name"),
            "date_range": date_range,
            "availability_by_day": availability_by_day,
            "average_availability": (
                sum(d.get("available_hours", 0) for d in availability_by_day)
                / len(availability_by_day)
                if availability_by_day
                else 0
            ),
        }

    async def _get_utilization(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Get utilization metrics.

        Returns utilization data and trends.
        """
        self.logger.info("Getting utilization metrics")

        # Calculate utilization for all resources
        utilization_data = []

        for resource_id, resource in self.resource_pool.items():
            utilization = await self._calculate_resource_utilization(resource_id)
            utilization_data.append(
                {
                    "resource_id": resource_id,
                    "resource_name": resource.get("name"),
                    "role": resource.get("role"),
                    "utilization": utilization,
                    "status": await self._get_utilization_status(utilization),
                }
            )

        # Calculate aggregate metrics
        average_utilization = (
            sum(u["utilization"] for u in utilization_data) / len(utilization_data)
            if utilization_data
            else 0
        )

        over_allocated = [u for u in utilization_data if u["utilization"] > 1.0]
        under_utilized = [u for u in utilization_data if u["utilization"] < 0.5]

        result = {
            "total_resources": len(utilization_data),
            "average_utilization": average_utilization,
            "target_utilization": self.utilization_target,
            "utilization_variance": average_utilization - self.utilization_target,
            "over_allocated_count": len(over_allocated),
            "under_utilized_count": len(under_utilized),
            "over_allocated_resources": over_allocated,
            "under_utilized_resources": under_utilized,
            "utilization_by_resource": utilization_data,
        }
        if self.analytics_client:
            self.analytics_client.record_metric("utilization.average", average_utilization)
            self.analytics_client.record_metric("utilization.over_allocated", len(over_allocated))
            self.analytics_client.record_metric("utilization.under_utilized", len(under_utilized))
        return result

    async def _identify_conflicts(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Identify resource allocation conflicts.

        Returns conflicts and resolution recommendations.
        """
        self.logger.info("Identifying resource conflicts")

        conflicts = []

        for resource_id in self.resource_pool.keys():
            resource_allocations = self._load_allocations(resource_id)
            # Check for overlapping allocations
            for i, alloc1 in enumerate(resource_allocations):
                for alloc2 in resource_allocations[i + 1 :]:
                    overlap = await self._check_allocation_overlap(alloc1, alloc2)

                    if overlap.get("has_overlap"):
                        # Calculate over-allocation
                        total_allocation = alloc1.get("allocation_percentage", 0) + alloc2.get(
                            "allocation_percentage", 0
                        )

                        if total_allocation > 100:
                            conflicts.append(
                                {
                                    "resource_id": resource_id,
                                    "resource_name": self.resource_pool.get(resource_id, {}).get(
                                        "name"
                                    ),
                                    "allocation_1": alloc1,
                                    "allocation_2": alloc2,
                                    "overlap_period": overlap.get("period"),
                                    "over_allocation_percentage": total_allocation - 100,
                                    "severity": "high" if total_allocation > 150 else "medium",
                                }
                            )

        # Generate resolution recommendations
        recommendations = await self._generate_conflict_recommendations(conflicts)

        return {
            "total_conflicts": len(conflicts),
            "conflicts": conflicts,
            "recommendations": recommendations,
        }

    async def _get_resource_pool(
        self, filters: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """Retrieve resource pool data."""
        role_filter = filters.get("role")
        location_filter = filters.get("location")
        status_filter = filters.get("status", "Active")

        filtered_resources = []

        resources = list(self.resource_pool.values())
        if not resources:
            resources = self.resource_store.list(tenant_id)
            for resource in resources:
                resource_id = resource.get("resource_id")
                if resource_id:
                    self.resource_pool[resource_id] = resource

        for resource in resources:
            if role_filter and resource.get("role") != role_filter:
                continue
            if location_filter and resource.get("location") != location_filter:
                continue
            if status_filter and resource.get("status") != status_filter:
                continue

            filtered_resources.append(resource)

        return {
            "total_resources": len(filtered_resources),
            "resources": filtered_resources,
            "filters_applied": filters,
        }

    # Helper methods

    async def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"REQ-{timestamp}"

    async def _generate_allocation_id(self) -> str:
        """Generate unique allocation ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"ALLOC-{timestamp}-{uuid.uuid4().hex[:6]}"

    async def _validate_resource_record(
        self, resource_profile: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        record = {
            "id": resource_profile.get("resource_id"),
            "tenant_id": tenant_id,
            "name": resource_profile.get("name"),
            "role": resource_profile.get("role"),
            "location": resource_profile.get("location"),
            "status": resource_profile.get("status"),
            "created_at": resource_profile.get("created_at"),
            "metadata": {
                "skills": resource_profile.get("skills"),
                "certifications": resource_profile.get("certifications"),
                "availability": resource_profile.get("availability"),
                "cost_rate": resource_profile.get("cost_rate"),
            },
        }
        report = evaluate_quality_rules("resource", record)
        return {
            "is_valid": report.is_valid,
            "issues": [issue.__dict__ for issue in report.issues],
        }

    async def _publish_allocation_event(
        self, allocation: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = ResourceAllocationCreatedEvent(
            event_name="resource.allocation.created",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "allocation_id": allocation.get("allocation_id", ""),
                "resource_id": allocation.get("resource_id", ""),
                "project_id": allocation.get("project_id", ""),
                "start_date": allocation.get("start_date", ""),
                "end_date": allocation.get("end_date", ""),
                "allocation_percentage": allocation.get("allocation_percentage", 0),
            },
        )
        await self.event_bus.publish("resource.allocation.created", event.model_dump())

    async def _publish_resource_event(self, event_name: str, payload: dict[str, Any]) -> None:
        await self.event_bus.publish(event_name, payload)
        try:
            self.event_publisher.publish(event_name, payload)
        except Exception as exc:
            self.logger.warning("Service bus publish failed", extra={"error": str(exc)})

    async def _notify_requester(self, request: dict[str, Any]) -> None:
        requester = request.get("requested_by")
        if not requester or not self.notification_service:
            return
        subject = f"Resource request {request.get('request_id')} status update"
        content = f"Request status: {request.get('status')}"
        try:
            self.notification_service.send_email(requester, subject, content)
        except Exception as exc:
            self.logger.warning("Failed to send requester notification", extra={"error": str(exc)})

    async def _notify_project_manager(self, request: dict[str, Any]) -> None:
        manager = request.get("project_manager")
        if not manager or not self.notification_service:
            return
        subject = f"Resource request approved for project {request.get('project_id')}"
        content = f"Allocated resource: {request.get('allocated_resource')}"
        try:
            self.notification_service.send_email(manager, subject, content)
        except Exception as exc:
            self.logger.warning("Failed to send manager notification", extra={"error": str(exc)})

    def _subscribe_to_events(self) -> None:
        def _handle_schedule_change(payload: dict[str, Any]) -> None:
            self.logger.info("Received schedule change event", extra={"payload": payload})

        def _handle_approval_decision(payload: dict[str, Any]) -> None:
            asyncio.create_task(self._process_approval_decision(payload))

        try:
            self.event_bus.subscribe("schedule.changed", _handle_schedule_change)
            self.event_bus.subscribe("approval.decision", _handle_approval_decision)
        except Exception as exc:
            self.logger.warning("Failed to subscribe to schedule events", extra={"error": str(exc)})

    async def _sync_hr_systems(self) -> None:
        profiles: list[dict[str, Any]] = []
        if self.graph_client:
            profiles.extend(await self._fetch_azure_ad_profiles())
        profiles.extend(await self._fetch_workday_profiles())
        profiles.extend(await self._fetch_sap_profiles())
        if self.hr_profile_provider:
            profiles.extend(list(self.hr_profile_provider()))
        elif self.config:
            profiles.extend(self.config.get("hr_profiles", []))

        merged = self._merge_profiles(profiles)
        active_resource_ids: set[str] = set()
        if not self.resource_pool:
            for resource in self.resource_store.list(self.default_tenant_id):
                resource_id = resource.get("resource_id")
                if resource_id:
                    self.resource_pool[resource_id] = resource
        for profile in merged:
            resource_id = profile.get("employee_id")
            if not resource_id:
                continue
            active_resource_ids.add(resource_id)
            resource_profile = {
                "resource_id": resource_id,
                "name": profile.get("name"),
                "role": profile.get("role"),
                "skills": profile.get("skills", []),
                "location": profile.get("location", "Unknown"),
                "cost_rate": profile.get("cost_rate", 0.0),
                "certifications": profile.get("certifications", []),
                "availability": profile.get("availability", 1.0),
                "status": profile.get("status", "Active"),
                "created_at": profile.get("created_at", datetime.utcnow().isoformat()),
                "source_system": profile.get("source_system", "unknown"),
            }
            if resource_id not in self.capacity_calendar:
                calendar_entry = {
                    "resource_id": resource_id,
                    "available_hours_per_day": self.default_working_hours_per_day,
                    "working_days": self.default_working_days,
                    "planned_leave": [],
                    "holidays": [],
                }
                self.capacity_calendar[resource_id] = calendar_entry
                self.calendar_store.upsert(self.default_tenant_id, resource_id, calendar_entry)
                await self._persist_resource_schedule(
                    resource_id,
                    calendar_entry,
                    tenant_id=self.default_tenant_id,
                    availability=resource_profile.get("availability", 1.0),
                )
            existing = self.resource_pool.get(resource_id)
            if not existing:
                self.resource_pool[resource_id] = resource_profile
                await self._store_canonical_profile(resource_id, profile, resource_profile)
                self.resource_store.upsert(
                    self.default_tenant_id, resource_id, resource_profile
                )
                await self._publish_resource_event("resource.added", resource_profile)
            else:
                if self._has_resource_changed(existing, resource_profile):
                    self.resource_pool[resource_id] = resource_profile
                    await self._store_canonical_profile(resource_id, profile, resource_profile)
                    self.resource_store.upsert(
                        self.default_tenant_id, resource_id, resource_profile
                    )
                    await self._publish_resource_event("resource.updated", resource_profile)
            if profile.get("status") == "Inactive":
                await self._deactivate_resource(resource_id, reason="hr_status")
        await self._deactivate_missing_resources(active_resource_ids)
        await self._index_skills()

    async def _fetch_azure_ad_profiles(self) -> list[dict[str, Any]]:
        if not self.graph_client:
            return []
        profiles: list[dict[str, Any]] = []
        for user in self.graph_client.list_users():
            user_id = user.get("id")
            if not user_id:
                continue
            skills = self.graph_client.list_user_skills(user_id)
            availability = 1.0
            try:
                if self.calendar_service:
                    busy_events = self.calendar_service.get_availability(
                        user_id, datetime.utcnow(), datetime.utcnow() + timedelta(days=30)
                    )
                else:
                    busy_events = self.graph_client.get_calendar_availability(
                        user_id, datetime.utcnow(), datetime.utcnow() + timedelta(days=30)
                    )
                busy_count = len([event for event in busy_events if event.get("showAs") != "free"])
                availability = max(0.0, 1.0 - min(busy_count / 20, 1.0))
            except Exception:
                availability = 1.0
            profiles.append(
                {
                    "employee_id": user.get("employeeId") or user_id,
                    "name": user.get("displayName"),
                    "email": user.get("mail"),
                    "role": user.get("jobTitle"),
                    "department": user.get("department"),
                    "skills": [skill for skill in skills if skill],
                    "availability": availability,
                    "source_system": "azure_ad",
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
        return profiles

    async def _fetch_workday_profiles(self) -> list[dict[str, Any]]:
        try:
            from connectors.sdk.src.base_connector import ConnectorCategory, ConnectorConfig
            from connectors.workday.src.workday_connector import WorkdayConnector
        except Exception:
            return []
        try:
            config = ConnectorConfig(
                connector_id="workday",
                name="Workday",
                category=ConnectorCategory.HRIS,
                enabled=True,
            )
            connector = WorkdayConnector(config)
            profiles = []
            for worker in connector.read("workers") or []:
                profiles.append(
                    {
                        "employee_id": worker.get("id"),
                        "name": worker.get("name"),
                        "status": worker.get("status", "Active"),
                        "source_system": "workday",
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
            return profiles
        except Exception as exc:
            self.logger.warning("Workday sync failed", extra={"error": str(exc)})
            return []

    async def _fetch_sap_profiles(self) -> list[dict[str, Any]]:
        try:
            from connectors.sdk.src.base_connector import ConnectorCategory, ConnectorConfig
            from connectors.sap_successfactors.src.sap_successfactors_connector import (
                SapSuccessFactorsConnector,
            )
        except Exception:
            return []
        try:
            config = ConnectorConfig(
                connector_id="sap_successfactors",
                name="SAP SuccessFactors",
                category=ConnectorCategory.HRIS,
                enabled=True,
            )
            connector = SapSuccessFactorsConnector(config)
            profiles = []
            for user in connector.read("users") or []:
                profiles.append(
                    {
                        "employee_id": user.get("userId"),
                        "name": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
                        "status": user.get("status", "Active"),
                        "source_system": "sap_successfactors",
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
            return profiles
        except Exception as exc:
            self.logger.warning("SAP SuccessFactors sync failed", extra={"error": str(exc)})
            return []

    def _merge_profiles(self, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for profile in profiles:
            key = (
                profile.get("employee_id")
                or profile.get("email")
                or profile.get("name")
                or str(uuid.uuid4())
            )
            existing = merged.get(key, {})
            combined = {**existing, **{k: v for k, v in profile.items() if v}}
            combined["employee_id"] = combined.get("employee_id") or key
            merged[key] = combined
        return list(merged.values())

    async def _index_skills(self) -> None:
        if not self.search_client or not self.search_client.is_configured():
            return
        documents = []
        embedding_client = self.embedding_client or EmbeddingClient(None, None, None)
        for resource_id, resource in self.resource_pool.items():
            skills_text = " ".join(self._get_effective_skills(resource))
            documents.append(
                {
                    "@search.action": "mergeOrUpload",
                    "resource_id": resource_id,
                    "skills": skills_text,
                    "role": resource.get("role"),
                    "availability": resource.get("availability", 1.0),
                    "cost_rate": resource.get("cost_rate", 0.0),
                    "embedding": embedding_client.get_embedding(skills_text),
                }
            )
        self.search_client.upload_documents(documents)
        self._skills_indexed = True

    async def _sync_training_records(self) -> None:
        if not self.training_client or not self.training_client.is_configured():
            return
        resource_ids = list(self.resource_pool.keys())
        if not resource_ids:
            return
        records = self.training_client.fetch_training_records(resource_ids)
        for record in records:
            resource_id = record.get("resource_id")
            if not resource_id:
                continue
            self.training_records[resource_id] = record
            await self._apply_training_record(resource_id, record)
        await self._index_skills()

    async def _process_approval_decision(self, payload: dict[str, Any]) -> None:
        approval_id = payload.get("approval_id")
        request_id = payload.get("request_id")
        if not approval_id or not request_id:
            return
        decision = payload.get("decision")
        if decision not in {"approved", "rejected"}:
            return
        await self._approve_request(
            request_id,
            {
                "approved": decision == "approved",
                "selected_resource_id": payload.get("selected_resource_id"),
                "comments": payload.get("comments", ""),
                "approver_id": payload.get("approver_id", "unknown"),
            },
            tenant_id=payload.get("tenant_id", self.default_tenant_id),
        )

    async def _refresh_capacity_allocations(self) -> None:
        allocations = []
        allocations.extend(await self._fetch_planview_allocations())
        allocations.extend(await self._fetch_jira_tempo_allocations())
        for allocation in allocations:
            resource_id = allocation.get("resource_id")
            if not resource_id:
                continue
            if resource_id not in self.allocations:
                self.allocations[resource_id] = []
            self.allocations[resource_id].append(allocation)
            self.repository.upsert_capacity_allocation(allocation)
            if self.db_service:
                await self.db_service.store(
                    "capacity_allocations", allocation.get("allocation_id", ""), allocation
                )
            if self.redis_client:
                allocation_id = allocation.get("allocation_id")
                if allocation_id:
                    self.redis_client.set(
                        f"allocation:{allocation_id}", json.dumps(allocation), ex=3600
                    )
                self.redis_client.rpush(
                    f"resource_allocations:{resource_id}", json.dumps(allocation)
                )

    async def _fetch_planview_allocations(self) -> list[dict[str, Any]]:
        try:
            from connectors.sdk.src.base_connector import ConnectorCategory, ConnectorConfig
            from connectors.planview.src.planview_connector import PlanviewConnector
        except Exception:
            return []
        try:
            config = ConnectorConfig(
                connector_id="planview",
                name="Planview",
                category=ConnectorCategory.PPM,
                enabled=True,
            )
            connector = PlanviewConnector(config)
            endpoint = os.getenv("PLANVIEW_CAPACITY_ENDPOINT", "/api/v1/resource-allocations")
            response = connector._request("GET", endpoint)
            data = response.json().get("items", [])
            allocations = []
            for item in data:
                allocations.append(
                    {
                        "allocation_id": item.get("id") or f"planview-{uuid.uuid4().hex}",
                        "resource_id": item.get("resourceId"),
                        "project_id": item.get("projectId"),
                        "start_date": item.get("startDate"),
                        "end_date": item.get("endDate"),
                        "allocation_percentage": float(item.get("allocationPercent", 0)),
                        "source_system": "planview",
                        "status": item.get("status", "Active"),
                    }
                )
            return allocations
        except Exception as exc:
            self.logger.warning("Planview allocation sync failed", extra={"error": str(exc)})
            return []

    async def _fetch_jira_tempo_allocations(self) -> list[dict[str, Any]]:
        tempo_url = os.getenv("JIRA_TEMPO_API_URL")
        tempo_token = os.getenv("JIRA_TEMPO_API_TOKEN")
        if not tempo_url or not tempo_token:
            return []
        try:
            import requests

            response = requests.get(
                f"{tempo_url}/worklogs",
                headers={"Authorization": f"Bearer {tempo_token}"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json().get("results", [])
            allocations = []
            for item in data:
                allocations.append(
                    {
                        "allocation_id": item.get("tempoWorklogId")
                        or f"tempo-{uuid.uuid4().hex}",
                        "resource_id": item.get("author", {}).get("accountId"),
                        "project_id": item.get("issue", {}).get("projectId"),
                        "start_date": item.get("startDate"),
                        "end_date": item.get("startDate"),
                        "allocation_percentage": float(item.get("timeSpentSeconds", 0))
                        / 3600
                        / self.default_working_hours_per_day
                        * 100,
                        "source_system": "jira_tempo",
                        "status": "Active",
                    }
                )
            return allocations
        except Exception as exc:
            self.logger.warning("Tempo allocation sync failed", extra={"error": str(exc)})
            return []

    async def _train_forecasting_models(
        self,
        capacity_series: list[float],
        demand_series: list[float],
        *,
        tenant_id: str,
        history_months: int,
    ) -> dict[str, Any]:
        if not self.ml_forecast_client or not self.ml_forecast_client.is_configured():
            return {}
        run_id = f"forecast-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        metadata = {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "history_months": history_months,
            "trained_at": datetime.utcnow().isoformat(),
        }
        capacity_model_name = f"{tenant_id}-capacity"
        demand_model_name = f"{tenant_id}-demand"
        capacity_info = self.ml_forecast_client.train_model(
            capacity_model_name,
            capacity_series,
            self.forecast_horizon_months,
            metadata={"series_type": "capacity", **metadata},
        )
        demand_info = self.ml_forecast_client.train_model(
            demand_model_name,
            demand_series,
            self.forecast_horizon_months,
            metadata={"series_type": "demand", **metadata},
        )
        metadata["capacity_model"] = capacity_info
        metadata["demand_model"] = demand_info
        if self.db_service:
            await self.db_service.store(
                "capacity_forecast_models",
                run_id,
                metadata,
            )
        if capacity_info:
            await self._store_model_in_azure_ml(capacity_model_name, capacity_info)
        if demand_info:
            await self._store_model_in_azure_ml(demand_model_name, demand_info)
        return metadata

    async def _store_model_in_azure_ml(self, model_name: str, model: dict[str, Any]) -> None:
        endpoint = os.getenv("AZURE_ML_ENDPOINT")
        api_key = os.getenv("AZURE_ML_API_KEY")
        if not endpoint or not api_key:
            return
        try:
            import requests

            response = requests.post(
                f"{endpoint}/models/register",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"name": model_name, "model": model},
                timeout=30,
            )
            response.raise_for_status()
        except Exception as exc:
            self.logger.warning("Azure ML model registration failed", extra={"error": str(exc)})

    async def _acquire_lock(self, key: str, ttl_seconds: int = 10) -> bool:
        if not self.redis_client:
            return True
        result = self.redis_client.set(key, "locked", nx=True, ex=ttl_seconds)
        return bool(result)

    async def _release_lock(self, key: str) -> None:
        if self.redis_client:
            self.redis_client.delete(key)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def _load_allocations(self, resource_id: str) -> list[dict[str, Any]]:
        if self.redis_client:
            cached = self.redis_client.lrange(f"resource_allocations:{resource_id}", 0, -1)
            if cached:
                parsed = []
                for item in cached:
                    try:
                        parsed.append(json.loads(item))
                    except json.JSONDecodeError:
                        continue
                if parsed:
                    return parsed
        return self.allocations.get(resource_id, [])

    async def _check_availability(
        self, resource_id: str, start_date: str, end_date: str, effort: float
    ) -> dict[str, Any]:
        """Check if resource is available for given period."""
        calendar = self.capacity_calendar.get(resource_id, {})
        allocations = self.allocations.get(resource_id, [])
        if not calendar:
            calendar = {
                "available_hours_per_day": self.default_working_hours_per_day,
                "working_days": self.default_working_days,
                "planned_leave": [],
                "holidays": [],
            }

        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        required_hours = calendar.get("available_hours_per_day", 8) * effort

        windows = []
        is_available = True
        current_date = start
        while current_date <= end:
            day_availability = await self._calculate_day_availability(
                resource_id, current_date, calendar, allocations
            )
            if day_availability.get("available_hours", 0) >= required_hours:
                windows.append(
                    {
                        "start": current_date.isoformat(),
                        "end": current_date.isoformat(),
                        "capacity": effort,
                    }
                )
            else:
                is_available = False
            current_date += timedelta(days=1)

        return {"is_available": is_available, "windows": windows}

    async def _determine_approver(self, request: dict[str, Any]) -> str:
        """Determine who should approve the request."""
        default_approver = self.approval_routing.get("default_approver", "resource_manager")
        requester = request.get("requested_by")
        requester_profile = self.org_structure.get(requester, {}) if requester else {}
        if requester_profile.get("manager"):
            return requester_profile["manager"]
        project_role = request.get("project_role") or request.get("role")
        if project_role:
            project_role_mapping = self.approval_routing.get("by_project_role", {})
            if project_role in project_role_mapping:
                return project_role_mapping[project_role]
        project_roles = request.get("project_roles", [])
        for role in project_roles or []:
            project_role_mapping = self.approval_routing.get("by_project_role", {})
            if role in project_role_mapping:
                return project_role_mapping[role]
        project_id = request.get("project_id")
        if project_id:
            project_mapping = self.approval_routing.get("by_project", {})
            if project_id in project_mapping:
                return project_mapping[project_id]
        department = request.get("department") or requester_profile.get("department")
        if department:
            dept_mapping = self.approval_routing.get("by_department", {})
            if department in dept_mapping:
                return dept_mapping[department]
        role = request.get("role") or requester_profile.get("role")
        if role:
            role_mapping = self.approval_routing.get("by_role", {})
            if role in role_mapping:
                return role_mapping[role]
        effort = float(request.get("effort", 0))
        for threshold in sorted(
            self.approval_routing.get("effort_thresholds", []),
            key=lambda item: float(item.get("threshold", 0)),
            reverse=True,
        ):
            if effort >= float(threshold.get("threshold", 0)):
                return threshold.get("approver", default_approver)
        return default_approver

    async def _calculate_skill_match_score(
        self, resource_skills: set, required_skills: set
    ) -> float:
        """Calculate skill match score."""
        if not required_skills:
            return 1.0

        matching_skills = resource_skills.intersection(required_skills)
        match_score = len(matching_skills) / len(required_skills)
        return match_score

    async def _get_performance_score(
        self, resource_id: str, project_context: dict[str, Any]
    ) -> float:
        """Get historical performance score for resource."""
        if resource_id in self.performance_scores:
            return self.performance_scores[resource_id]
        if self.redis_client:
            cached = self.redis_client.get(f"resource_performance:{resource_id}")
            if cached:
                try:
                    score = float(cached)
                    self.performance_scores[resource_id] = score
                    return score
                except ValueError:
                    pass
        score = 0.85
        if self.db_service:
            records = await self.db_service.query(
                "project_performance", {"resource_id": resource_id}, limit=50
            )
            if records:
                score = self._calculate_performance_score(records, project_context)
        self.performance_scores[resource_id] = score
        if self.db_service:
            await self.db_service.store(
                "resource_performance_scores",
                resource_id,
                {
                    "resource_id": resource_id,
                    "score": score,
                    "calculated_at": datetime.utcnow().isoformat(),
                },
            )
        self.repository.upsert_performance_score(
            resource_id, score, {"calculated_at": datetime.utcnow().isoformat()}
        )
        if self.redis_client:
            self.redis_client.set(f"resource_performance:{resource_id}", score, ex=3600)
        return score

    async def _calculate_total_capacity(self) -> float:
        """Calculate total resource capacity in FTE."""
        total_capacity = 0.0
        for resource in self.resource_pool.values():
            if resource.get("status") != "Active":
                continue
            total_capacity += float(resource.get("availability", 0.0))
        return total_capacity

    async def _calculate_total_demand(self) -> float:
        """Calculate total resource demand in FTE."""
        total_demand = 0
        for allocations_list in self.allocations.values():
            for alloc in allocations_list:
                if alloc.get("status") == "Active":
                    total_demand += alloc.get("allocation_percentage", 0) / 100
        return total_demand

    async def _build_capacity_demand_history(self, months: int) -> tuple[list[float], list[float]]:
        """Build historical capacity and demand series."""
        if months <= 0:
            return [], []
        now = datetime.utcnow()
        capacity_value = await self._calculate_total_capacity()
        capacity_series: list[float] = []
        demand_series: list[float] = []
        for offset in range(-months + 1, 1):
            month_start = self._month_start(now, offset)
            month_end = self._month_start(now, offset + 1) - timedelta(days=1)
            month_days = max((month_end - month_start).days + 1, 1)
            month_demand = 0.0
            for allocations_list in self.allocations.values():
                for alloc in allocations_list:
                    if alloc.get("status") != "Active":
                        continue
                    alloc_start_str = alloc.get("start_date")
                    alloc_end_str = alloc.get("end_date")
                    if not isinstance(alloc_start_str, str) or not isinstance(alloc_end_str, str):
                        continue
                    alloc_start = datetime.fromisoformat(alloc_start_str)
                    alloc_end = datetime.fromisoformat(alloc_end_str)
                    if alloc_end < month_start or alloc_start > month_end:
                        continue
                    overlap_start = max(alloc_start, month_start)
                    overlap_end = min(alloc_end, month_end)
                    overlap_days = max((overlap_end - overlap_start).days + 1, 0)
                    allocation_fte = float(alloc.get("allocation_percentage", 0)) / 100
                    month_demand += allocation_fte * (overlap_days / month_days)
            capacity_series.append(capacity_value)
            demand_series.append(month_demand)
        return capacity_series, demand_series

    @staticmethod
    def _month_start(base: datetime, offset: int) -> datetime:
        """Return the first day of the month offset from base."""
        month_index = base.month - 1 + offset
        year = base.year + month_index // 12
        month = month_index % 12 + 1
        return datetime(year, month, 1)

    async def _forecast_future_capacity(self, months: int) -> list[dict[str, Any]]:
        """Forecast future capacity."""
        # Future work: Use ML model for forecasting
        # Baseline: assume constant capacity
        current_capacity = await self._calculate_total_capacity()
        return [{"month": i, "capacity": current_capacity} for i in range(months)]

    async def _forecast_future_demand(self, months: int) -> list[dict[str, Any]]:
        """Forecast future demand."""
        # Future work: Use ML model and project pipeline data
        # Baseline
        return [
            {"month": i, "demand": 0.8 * await self._calculate_total_capacity()}
            for i in range(months)
        ]

    async def _identify_capacity_bottlenecks(
        self, capacity: list[dict[str, Any]], demand: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Identify capacity bottlenecks."""
        bottlenecks: list[dict[str, Any]] = []
        for i, (cap, dem) in enumerate(zip(capacity, demand)):
            dem_value = float(dem.get("demand", 0))
            cap_value = float(cap.get("capacity", 0))
            if dem_value > cap_value:
                bottlenecks.append(
                    {
                        "month": i,
                        "capacity": cap_value,
                        "demand": dem_value,
                        "shortfall": dem_value - cap_value,
                    }
                )
        return bottlenecks

    async def _generate_capacity_recommendations(
        self, bottlenecks: list[dict[str, Any]]
    ) -> list[str]:
        """Generate capacity recommendations."""
        recommendations = []
        if bottlenecks:
            recommendations.append(f"Capacity shortfall identified in {len(bottlenecks)} periods")
            recommendations.append("Consider hiring additional resources or outsourcing")
            recommendations.append("Review project priorities and timelines")
        return recommendations

    async def _identify_capacity_gaps(self, forecast: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify capacity gaps."""
        return forecast.get("bottlenecks", [])  # type: ignore

    async def _generate_mitigation_strategies(
        self, gaps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate mitigation strategies for capacity gaps."""
        return [
            {"strategy": "Hire permanent staff", "timeline": "3-6 months"},
            {"strategy": "Engage contractors", "timeline": "1-2 months"},
            {"strategy": "Cross-train existing staff", "timeline": "2-3 months"},
        ]

    async def _generate_hiring_recommendations(
        self, gaps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate hiring recommendations."""
        return [
            {"role": "Software Developer", "count": 2, "priority": "high"},
            {"role": "Project Manager", "count": 1, "priority": "medium"},
        ]

    async def _generate_training_recommendations(
        self, gaps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate training recommendations."""
        return [
            {"skill": "Cloud Architecture", "target_count": 3, "priority": "high"},
            {"skill": "Agile Methodologies", "target_count": 5, "priority": "medium"},
        ]

    async def _create_baseline_scenario(self) -> dict[str, Any]:
        """Create baseline scenario."""
        history_months = 6
        capacity_series, demand_series = await self._build_capacity_demand_history(history_months)
        forecast = await self._forecast_capacity({"history_months": history_months})
        utilization = await self._calculate_total_demand()
        total_capacity = await self._calculate_total_capacity()
        return {
            "resource_count": len(self.resource_pool),
            "allocations": self.allocations,
            "utilization": utilization / total_capacity if total_capacity else 0.0,
            "capacity_series": capacity_series,
            "demand_series": demand_series,
            "forecast": forecast,
            "average_cost_rate": self._average_cost_rate(),
        }

    async def _apply_scenario_changes(
        self, baseline: dict[str, Any], changes: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply changes to create scenario."""
        scenario = dict(baseline)
        added_resources = changes.get("add_resources", [])
        removed_resources = changes.get("remove_resources", [])
        scope_multiplier = float(changes.get("scope_multiplier", 1.0))
        capacity_multiplier = float(changes.get("capacity_multiplier", 1.0))

        scenario["resource_count"] = max(
            0, baseline.get("resource_count", 0) + len(added_resources) - len(removed_resources)
        )
        scenario["capacity_multiplier"] = capacity_multiplier
        scenario["scope_multiplier"] = scope_multiplier
        scenario["added_resources"] = added_resources
        scenario["removed_resources"] = removed_resources
        return scenario

    async def _calculate_scenario_metrics(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Calculate metrics for scenario."""
        forecast = await self._forecast_capacity_for_scenario(scenario)
        avg_capacity = sum(item["capacity"] for item in forecast["future_capacity"]) / max(
            len(forecast["future_capacity"]), 1
        )
        avg_demand = sum(item["demand"] for item in forecast["future_demand"]) / max(
            len(forecast["future_demand"]), 1
        )
        avg_utilization = avg_demand / avg_capacity if avg_capacity else 0.0
        average_cost_rate = scenario.get("average_cost_rate", 0.0)
        cost_impact = avg_demand * average_cost_rate
        schedule_impact = max(0.0, avg_demand - avg_capacity)
        return {
            "average_utilization": avg_utilization,
            "resource_count": scenario.get("resource_count", 0),
            "average_capacity": avg_capacity,
            "average_demand": avg_demand,
            "forecast": forecast,
            "cost_impact": cost_impact,
            "schedule_impact": schedule_impact,
        }

    async def _compare_scenarios(
        self, baseline: dict[str, Any], scenario: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare scenarios."""
        return {
            "utilization_difference": scenario.get("average_utilization", 0)
            - baseline.get("average_utilization", 0),
            "resource_count_difference": scenario.get("resource_count", 0)
            - baseline.get("resource_count", 0),
            "cost_difference": scenario.get("cost_impact", 0)
            - baseline.get("cost_impact", 0),
            "schedule_difference": scenario.get("schedule_impact", 0)
            - baseline.get("schedule_impact", 0),
        }

    async def _generate_scenario_recommendation(self, comparison: dict[str, Any]) -> str:
        """Generate recommendation based on scenario comparison."""
        util_diff = comparison.get("utilization_difference", 0)
        if util_diff > 0.1:
            return "Scenario improves utilization significantly. Recommended."
        elif util_diff < -0.1:
            return "Scenario decreases utilization. Not recommended."
        else:
            return "Scenario has minimal impact on utilization."

    async def _validate_allocation(
        self, resource_id: str, start_date: str, end_date: str, allocation_percentage: float
    ) -> dict[str, Any]:
        """Validate allocation request."""
        # Check if resource exists
        if resource_id not in self.resource_pool:
            return {"valid": False, "reason": "Resource not found"}

        # Check if allocation percentage is valid
        if allocation_percentage <= 0 or allocation_percentage > 100:
            return {"valid": False, "reason": "Invalid allocation percentage"}

        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        allocations = self._load_allocations(resource_id)
        total_overlap = allocation_percentage
        overlapping_allocations = 0
        for alloc in allocations:
            overlap = await self._check_allocation_overlap(
                alloc,
                {
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            if overlap.get("has_overlap"):
                overlapping_allocations += 1
                total_overlap += float(alloc.get("allocation_percentage", 0))
        if (
            self.enforce_allocation_constraints
            and overlapping_allocations >= self.max_concurrent_allocations
        ):
            return {
                "valid": False,
                "reason": "Allocation exceeds maximum concurrent allocation constraint",
            }
        if total_overlap > (self.max_allocation_threshold * 100):
            return {
                "valid": False,
                "reason": "Allocation exceeds maximum capacity threshold",
            }
        if start > end:
            return {"valid": False, "reason": "Start date must be before end date"}

        return {"valid": True}

    async def _update_resource_availability(self, resource_id: str) -> None:
        """Update resource availability based on allocations."""
        allocations = self.allocations.get(resource_id, [])

        # Calculate total allocation
        total_allocation = sum(
            alloc.get("allocation_percentage", 0)
            for alloc in allocations
            if alloc.get("status") == "Active"
        )

        # Update availability
        availability = max(0, 100 - total_allocation) / 100
        training_load = float(self.resource_pool.get(resource_id, {}).get("training_load", 0.0))
        availability = max(0.0, availability - training_load)
        self.resource_pool[resource_id]["availability"] = availability
        schedule = self.capacity_calendar.get(resource_id, {})
        await self._persist_resource_schedule(
            resource_id,
            schedule,
            tenant_id=self.default_tenant_id,
            availability=availability,
        )
        if self.db_service:
            await self.db_service.store(
                "resource_availability",
                resource_id,
                {
                    "resource_id": resource_id,
                    "availability": availability,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )

    async def _calculate_day_availability(
        self,
        resource_id: str,
        date: datetime,
        calendar: dict[str, Any],
        allocations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate availability for a specific day."""
        # Check if it's a working day
        weekday = date.weekday()
        if weekday not in calendar.get("working_days", []):
            return {"date": date.isoformat(), "available_hours": 0, "reason": "Non-working day"}

        total_hours = calendar.get("available_hours_per_day", self.default_working_hours_per_day)
        date_str = date.date().isoformat()
        holidays = {str(day) for day in calendar.get("holidays", [])}
        if date_str in holidays:
            return {
                "date": date.isoformat(),
                "total_hours": total_hours,
                "available_hours": 0,
                "reason": "Holiday",
            }
        for leave in calendar.get("planned_leave", []):
            start_str = leave.get("start_date")
            end_str = leave.get("end_date")
            if not isinstance(start_str, str) or not isinstance(end_str, str):
                continue
            leave_start = datetime.fromisoformat(start_str)
            leave_end = datetime.fromisoformat(end_str)
            if leave_start.date() <= date.date() <= leave_end.date():
                leave_hours = float(leave.get("hours", total_hours))
                available_hours = max(0.0, total_hours - leave_hours)
                return {
                    "date": date.isoformat(),
                    "total_hours": total_hours,
                    "available_hours": available_hours,
                    "reason": leave.get("reason", "Planned leave"),
                }

        # Calculate allocated hours
        allocated_hours = 0
        for alloc in allocations:
            alloc_start_str = alloc.get("start_date")
            alloc_end_str = alloc.get("end_date")
            if not isinstance(alloc_start_str, str) or not isinstance(alloc_end_str, str):
                continue
            alloc_start = datetime.fromisoformat(alloc_start_str)
            alloc_end = datetime.fromisoformat(alloc_end_str)

            if alloc_start <= date <= alloc_end:
                daily_hours = calendar.get("available_hours_per_day", 8)
                allocated_hours += daily_hours * (alloc.get("allocation_percentage", 0) / 100)

        # Calculate available hours
        total_hours = calendar.get("available_hours_per_day", self.default_working_hours_per_day)
        available_hours = max(0, total_hours - allocated_hours)

        return {
            "date": date.isoformat(),
            "total_hours": total_hours,
            "allocated_hours": allocated_hours,
            "available_hours": available_hours,
        }

    async def _calculate_resource_utilization(self, resource_id: str) -> float:
        """Calculate utilization for a resource."""
        allocations = self.allocations.get(resource_id, [])

        total_allocation = sum(
            float(alloc.get("allocation_percentage", 0))
            for alloc in allocations
            if alloc.get("status") == "Active"
        )

        return cast(float, total_allocation / 100)  # type: ignore

    async def _get_utilization_status(self, utilization: float) -> str:
        """Get utilization status."""
        if utilization > 1.0:
            return "Over-allocated"
        elif utilization >= self.utilization_target:
            return "Optimal"
        elif utilization >= 0.5:
            return "Under-utilized"
        else:
            return "Significantly Under-utilized"

    async def _check_allocation_overlap(
        self, alloc1: dict[str, Any], alloc2: dict[str, Any]
    ) -> dict[str, Any]:
        """Check if two allocations overlap."""
        start1_str = alloc1.get("start_date")
        end1_str = alloc1.get("end_date")
        start2_str = alloc2.get("start_date")
        end2_str = alloc2.get("end_date")
        assert isinstance(start1_str, str) and isinstance(
            end1_str, str
        ), "alloc1 dates must be strings"
        assert isinstance(start2_str, str) and isinstance(
            end2_str, str
        ), "alloc2 dates must be strings"
        start1 = datetime.fromisoformat(start1_str)
        end1 = datetime.fromisoformat(end1_str)
        start2 = datetime.fromisoformat(start2_str)
        end2 = datetime.fromisoformat(end2_str)

        # Check for overlap
        has_overlap = not (end1 < start2 or end2 < start1)

        if has_overlap:
            overlap_start = max(start1, start2)
            overlap_end = min(end1, end2)
            return {
                "has_overlap": True,
                "period": {"start": overlap_start.isoformat(), "end": overlap_end.isoformat()},
            }

        return {"has_overlap": False}

    async def _store_canonical_profile(
        self,
        resource_id: str,
        canonical_profile: dict[str, Any],
        resource_profile: dict[str, Any],
    ) -> None:
        self.repository.upsert_employee_profile(canonical_profile)
        if self.db_service:
            await self.db_service.store("employee_profiles", resource_id, canonical_profile)
            await self.db_service.store("resource_profiles", resource_id, resource_profile)

    async def _generate_conflict_recommendations(
        self, conflicts: list[dict[str, Any]]
    ) -> list[str]:
        """Generate recommendations for resolving conflicts."""
        recommendations = []
        for conflict in conflicts:
            severity = conflict.get("severity")
            if severity == "high":
                recommendations.append(
                    f"Critical: Resource {conflict.get('resource_name')} is over-allocated by "
                    f"{conflict.get('over_allocation_percentage')}%. "
                    "Consider reallocating or adding resources."
                )
        return recommendations

    async def _optimize_resource_allocations(
        self, planning_horizon: dict[str, Any]
    ) -> dict[str, Any]:
        """Optimize resource allocations using a greedy assignment strategy."""
        pending_requests = [
            request
            for request in self.demand_requests.values()
            if request.get("status") == "Pending"
        ]
        pending_requests.extend(planning_horizon.get("requests", []))
        pending_requests.sort(
            key=lambda req: (-(req.get("effort", 1.0)), req.get("start_date", ""))
        )

        availability = {
            resource_id: float(resource.get("availability", 0.0))
            for resource_id, resource in self.resource_pool.items()
        }
        allocations: list[dict[str, Any]] = []
        unfilled: list[dict[str, Any]] = []

        for request in pending_requests:
            required_skills = request.get("required_skills", [])
            effort = float(request.get("effort", 1.0))
            request_id = request.get("request_id") or request.get("id") or "pending"
            matches = await self._find_matching_resources(
                required_skills, availability_floor=effort
            )
            assigned = False
            for match in matches:
                resource_id = match["resource_id"]
                if availability.get(resource_id, 0.0) >= effort:
                    availability[resource_id] = max(
                        0.0, availability.get(resource_id, 0.0) - effort
                    )
                    allocations.append(
                        {
                            "request_id": request_id,
                            "resource_id": resource_id,
                            "score": match.get("weighted_score"),
                            "effort": effort,
                        }
                    )
                    assigned = True
                    break
            if not assigned:
                unfilled.append(
                    {
                        "request_id": request_id,
                        "required_skills": required_skills,
                        "effort": effort,
                    }
                )

        return {
            "proposed_allocations": allocations,
            "unfilled_requests": unfilled,
            "remaining_capacity": availability,
        }

    async def _apply_training_record(
        self, resource_id: str, record: dict[str, Any]
    ) -> dict[str, Any]:
        resource = self.resource_pool.get(resource_id)
        if not resource:
            return {}
        completed = record.get("completed", [])
        in_progress = record.get("in_progress", [])
        scheduled = record.get("scheduled", [])
        certifications = record.get("certifications", [])
        skills = record.get("skills", [])
        training_load = self._calculate_training_load(record)
        training_metadata = {
            "completed": completed,
            "in_progress": in_progress,
            "scheduled": scheduled,
            "certifications": certifications,
            "skills": skills,
            "training_load": training_load,
            "updated_at": datetime.utcnow().isoformat(),
        }
        resource["training"] = training_metadata
        resource["training_load"] = training_load
        resource["certifications"] = list(
            {*(resource.get("certifications", []) or []), *certifications}
        )
        resource["skills"] = list(
            {*(resource.get("skills", []) or []), *skills}
        )
        if self.db_service:
            await self.db_service.store(
                "resource_training",
                resource_id,
                {"resource_id": resource_id, **training_metadata},
            )
        await self._update_resource_availability(resource_id)
        return training_metadata

    def _calculate_training_load(self, record: dict[str, Any]) -> float:
        weekly_hours = record.get("weekly_hours")
        total_hours = record.get("total_hours")
        weeks = record.get("weeks", 1)
        if weekly_hours is None and total_hours is not None:
            weekly_hours = float(total_hours) / max(float(weeks or 1), 1.0)
        if weekly_hours is None:
            weekly_hours = 0.0
        total_work_hours = self.default_working_hours_per_day * len(self.default_working_days)
        return min(max(float(weekly_hours) / max(total_work_hours, 1.0), 0.0), 1.0)

    def _get_effective_skills(self, resource: dict[str, Any]) -> list[str]:
        skills = set(resource.get("skills", []) or [])
        training = resource.get("training", {}) if resource else {}
        for skill in training.get("skills", []) or []:
            skills.add(skill)
        for cert in training.get("certifications", []) or []:
            skills.add(cert)
        return list(skills)

    def _calculate_performance_score(
        self, records: list[dict[str, Any]], project_context: dict[str, Any]
    ) -> float:
        weights = {
            "on_time_rate": 0.3,
            "quality_score": 0.25,
            "completion_rate": 0.2,
            "customer_satisfaction": 0.15,
            "utilization_rate": 0.1,
        }
        total = 0.0
        metric_totals = {key: 0.0 for key in weights}
        for record in records:
            on_time = self._normalize_score(record.get("on_time_rate", 0.85))
            quality = self._normalize_score(record.get("quality_score", 0.85))
            completion = self._normalize_score(record.get("completion_rate", 0.85))
            satisfaction = self._normalize_score(record.get("customer_satisfaction", 0.85))
            utilization = self._normalize_score(record.get("utilization_rate", 0.85))
            total += (
                weights["on_time_rate"] * on_time
                + weights["quality_score"] * quality
                + weights["completion_rate"] * completion
                + weights["customer_satisfaction"] * satisfaction
                + weights["utilization_rate"] * utilization
            )
            metric_totals["on_time_rate"] += on_time
            metric_totals["quality_score"] += quality
            metric_totals["completion_rate"] += completion
            metric_totals["customer_satisfaction"] += satisfaction
            metric_totals["utilization_rate"] += utilization
        average = total / max(len(records), 1)
        context_boost = 0.0
        if project_context.get("priority") == "high":
            context_boost += 0.02
        if self.analytics_client:
            record_count = max(len(records), 1)
            for metric_name, total_value in metric_totals.items():
                self.analytics_client.record_metric(
                    f"resource.performance.{metric_name}",
                    total_value / record_count,
                )
        return min(1.0, max(0.0, average + context_boost))

    def _normalize_score(self, value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.85
        if numeric > 1.0:
            numeric = numeric / 100.0
        return min(1.0, max(0.0, numeric))

    def _get_attrition_rate(self) -> float:
        if self.attrition_rate:
            return self.attrition_rate
        return 0.0

    def _seasonality_multiplier(self, month_offset: int) -> float:
        now = datetime.utcnow()
        target_month = (now.month - 1 + month_offset) % 12 + 1
        return float(self.seasonality_factors.get(str(target_month), 1.0))

    def _adjust_capacity_forecast(self, forecast: list[float]) -> list[dict[str, Any]]:
        adjusted: list[dict[str, Any]] = []
        attrition_rate = self._get_attrition_rate()
        training_adjustments = self._training_capacity_adjustments(len(forecast))
        uplift = self._skill_development_multiplier()
        for index, value in enumerate(forecast):
            seasonality = self._seasonality_multiplier(index)
            adjusted_value = max(
                0.0,
                (value * (1 - attrition_rate) * seasonality * uplift)
                - training_adjustments[index],
            )
            adjusted.append({"month": index + 1, "capacity": adjusted_value})
        return adjusted

    def _adjust_demand_forecast(self, forecast: list[float]) -> list[dict[str, Any]]:
        adjusted: list[dict[str, Any]] = []
        pipeline_adjustments = self._pipeline_demand_adjustments(len(forecast))
        for index, value in enumerate(forecast):
            seasonality = self._seasonality_multiplier(index)
            adjusted_value = max(0.0, (value + pipeline_adjustments[index]) * seasonality)
            adjusted.append({"month": index + 1, "demand": adjusted_value})
        return adjusted

    def _training_capacity_adjustments(self, horizon: int) -> list[float]:
        adjustments = [0.0 for _ in range(horizon)]
        total_work_hours = self.default_working_hours_per_day * len(self.default_working_days)
        if total_work_hours == 0:
            return adjustments
        for record in self.training_records.values():
            for session in record.get("scheduled", []) or []:
                date_str = session.get("date")
                hours = float(session.get("hours", 0.0))
                if not date_str:
                    continue
                session_date = datetime.fromisoformat(date_str)
                month_offset = (
                    (session_date.year - datetime.utcnow().year) * 12
                    + session_date.month
                    - datetime.utcnow().month
                )
                if 0 <= month_offset < horizon:
                    adjustments[month_offset] += hours / max(total_work_hours, 1.0)
        return [value * self.training_capacity_impact for value in adjustments]

    def _pipeline_demand_adjustments(self, horizon: int) -> list[float]:
        adjustments = [0.0 for _ in range(horizon)]
        pipeline = self.config.get("pipeline_forecast", []) if self.config else []
        for entry in pipeline:
            month = int(entry.get("month", 0)) - 1
            demand = float(entry.get("demand", 0.0))
            if 0 <= month < horizon:
                adjustments[month] += demand
        return adjustments

    def _skill_development_multiplier(self) -> float:
        if not self.training_records:
            return 1.0
        completed_count = sum(
            len(record.get("completed", []) or []) for record in self.training_records.values()
        )
        resource_count = max(len(self.resource_pool), 1)
        uplift = min(self.skill_development_uplift, completed_count / (resource_count * 10))
        return 1.0 + uplift

    async def _deactivate_resource(self, resource_id: str, *, reason: str) -> None:
        resource = self.resource_pool.get(resource_id)
        if not resource:
            return
        if resource.get("status") == "Inactive":
            return
        resource["status"] = "Inactive"
        resource["deactivated_at"] = datetime.utcnow().isoformat()
        resource["deactivation_reason"] = reason
        self.resource_pool[resource_id] = resource
        self.resource_store.upsert(self.default_tenant_id, resource_id, resource)
        await self._publish_resource_event("resource.updated", resource)

    async def _deactivate_missing_resources(self, active_resource_ids: set[str]) -> None:
        if not active_resource_ids:
            return
        for resource_id, resource in list(self.resource_pool.items()):
            if resource_id in active_resource_ids:
                continue
            source = resource.get("source_system")
            if source in {"azure_ad", "workday", "sap_successfactors"}:
                await self._deactivate_resource(resource_id, reason="missing_from_hr_sync")

    def _has_resource_changed(
        self, existing: dict[str, Any], updated: dict[str, Any]
    ) -> bool:
        fields = [
            "name",
            "role",
            "skills",
            "location",
            "cost_rate",
            "certifications",
            "availability",
            "status",
            "source_system",
        ]
        for field in fields:
            if existing.get(field) != updated.get(field):
                return True
        return False

    async def _forecast_capacity_for_scenario(
        self, scenario: dict[str, Any]
    ) -> dict[str, Any]:
        history_months = 6
        capacity_series, demand_series = await self._build_capacity_demand_history(history_months)
        scope_multiplier = float(scenario.get("scope_multiplier", 1.0))
        capacity_multiplier = float(scenario.get("capacity_multiplier", 1.0))
        resource_count = int(scenario.get("resource_count", len(self.resource_pool)))
        base_count = len(self.resource_pool) or 1
        adjusted_capacity_series = [
            value * (resource_count / base_count) * capacity_multiplier
            for value in capacity_series
        ]
        adjusted_demand_series = [value * scope_multiplier for value in demand_series]
        forecaster = TimeSeriesForecaster(
            automl_endpoint=os.getenv("AZURE_AUTOML_ENDPOINT"),
            automl_api_key=os.getenv("AZURE_AUTOML_API_KEY"),
        )
        capacity_forecast = forecaster.forecast(
            adjusted_capacity_series, self.forecast_horizon_months
        )
        demand_forecast = forecaster.forecast(
            adjusted_demand_series, self.forecast_horizon_months
        )
        return {
            "future_capacity": [
                {"month": index + 1, "capacity": max(0.0, value)}
                for index, value in enumerate(capacity_forecast)
            ],
            "future_demand": [
                {"month": index + 1, "demand": max(0.0, value)}
                for index, value in enumerate(demand_forecast)
            ],
        }

    def _average_cost_rate(self) -> float:
        if not self.resource_pool:
            return 0.0
        return sum(float(resource.get("cost_rate", 0.0)) for resource in self.resource_pool.values()) / len(
            self.resource_pool
        )

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Resource & Capacity Management Agent...")
        if self.redis_client:
            try:
                self.redis_client.close()
            except Exception as exc:
                self.logger.warning("Failed to close Redis client", extra={"error": str(exc)})
        if self.db_service:
            try:
                await self.db_service.store(
                    "agent_events",
                    f"resource-capacity-cleanup-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    {"status": "cleanup", "timestamp": datetime.utcnow().isoformat()},
                )
            except Exception as exc:
                self.logger.warning("Failed to flush events", extra={"error": str(exc)})
        self.repository.close()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "resource_pool_management",
            "demand_intake",
            "skill_matching",
            "capacity_planning",
            "capacity_forecasting",
            "scenario_modeling",
            "resource_allocation",
            "availability_tracking",
            "utilization_monitoring",
            "conflict_identification",
            "approval_routing",
            "cross_project_management",
            "what_if_analysis",
        ]

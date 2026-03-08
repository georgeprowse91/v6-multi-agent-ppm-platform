"""
Data models and persistence stores for Stakeholder & Communications Management Agent.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

# SQLAlchemy (optional) — guarded with try/except so transitive-dep failures
# don't prevent the module from loading.
try:
    from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, Text, create_engine
except (ImportError, Exception):
    create_engine = None  # type: ignore[assignment,misc]
    Table = None  # type: ignore[assignment,misc]
    Column = None  # type: ignore[assignment,misc]
    String = None  # type: ignore[assignment,misc]
    Text = None  # type: ignore[assignment,misc]
    DateTime = None  # type: ignore[assignment,misc]
    MetaData = None  # type: ignore[assignment,misc]
    JSON = None  # type: ignore[assignment,misc]

# Azure Service Bus (optional)
try:
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
except (ImportError, Exception):
    ServiceBusClient = None  # type: ignore[assignment,misc]
    ServiceBusMessage = None  # type: ignore[assignment,misc]


class CommunicationHistoryStore:
    """Persist communications history to a database backend."""

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url
        self._engine = None
        self._table = None
        self._sqlite_conn = None
        if create_engine:
            self._engine = create_engine(db_url, future=True)
            metadata = MetaData()
            metadata_table = Table(
                "communications_history",
                metadata,
                Column("record_id", String, primary_key=True),
                Column("stakeholder_id", String),
                Column("channel", String),
                Column("subject", String),
                Column("status", String),
                Column("content", Text),
                Column("metadata", JSON),
                Column("created_at", DateTime),
            )
            metadata.create_all(self._engine)
            self._table = metadata_table
        else:
            self._sqlite_conn = sqlite3.connect(self._sqlite_path(db_url))
            self._sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS communications_history (
                    record_id TEXT PRIMARY KEY,
                    stakeholder_id TEXT,
                    channel TEXT,
                    subject TEXT,
                    status TEXT,
                    content TEXT,
                    metadata TEXT,
                    created_at TEXT
                )
                """)
            self._sqlite_conn.commit()

    def _sqlite_path(self, db_url: str) -> str:
        if db_url.startswith("sqlite:///"):
            return db_url.replace("sqlite:///", "")
        if db_url.startswith("sqlite://"):
            return db_url.replace("sqlite://", "")
        return ":memory:"

    def add_record(self, record: dict[str, Any]) -> None:
        if self._engine and self._table is not None:
            with self._engine.begin() as conn:
                conn.execute(self._table.insert().values(**record))
            return
        if self._sqlite_conn:
            self._sqlite_conn.execute(
                """
                INSERT OR REPLACE INTO communications_history (
                    record_id, stakeholder_id, channel, subject, status, content, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("record_id"),
                    record.get("stakeholder_id"),
                    record.get("channel"),
                    record.get("subject"),
                    record.get("status"),
                    record.get("content"),
                    json.dumps(record.get("metadata")),
                    record.get("created_at"),
                ),
            )
            self._sqlite_conn.commit()

    def close(self) -> None:
        if self._engine:
            self._engine.dispose()
        if self._sqlite_conn:
            self._sqlite_conn.close()


class ServiceBusPublisher:
    """Publish communication events to Azure Service Bus."""

    def __init__(
        self, connection_string: str | None, topic_name: str | None, queue_name: str | None
    ) -> None:
        self.connection_string = connection_string
        self.topic_name = topic_name
        self.queue_name = queue_name
        self.enabled = (
            bool(connection_string)
            and ServiceBusClient is not None
            and ServiceBusMessage is not None
        )

    def publish(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled or (not self.topic_name and not self.queue_name):
            return {"status": "skipped", "reason": "service_bus_unavailable"}
        body = json.dumps({"event_type": event_type, "payload": payload})
        with ServiceBusClient.from_connection_string(self.connection_string) as client:
            if self.topic_name:
                with client.get_topic_sender(self.topic_name) as sender:
                    sender.send_messages(ServiceBusMessage(body))
            else:
                with client.get_queue_sender(self.queue_name) as sender:
                    sender.send_messages(ServiceBusMessage(body))
        return {"status": "published", "event_type": event_type}

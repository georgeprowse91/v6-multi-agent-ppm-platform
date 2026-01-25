from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .db import get_conn, init_db
from .security import User
from .utils import json_dumps_compact, json_loads, new_id, now_iso


@dataclass
class Entity:
    id: str
    type: str
    title: str
    status: str
    classification: str
    data: dict[str, Any]
    created_at: str
    updated_at: str


class Store:
    """SQLite-backed store for the prototype.

    Uses a flexible JSON payload per entity type to avoid over-designing a schema for a prototype.
    """

    def __init__(self, db_file: Path):
        self.db_file = db_file
        self.conn: sqlite3.Connection = get_conn(db_file)
        init_db(self.conn)

    @staticmethod
    def default_db_file() -> Path:
        # apps/web/ppm/store.py -> apps/web/data/ppm.db
        prototype_root = Path(__file__).resolve().parents[1]
        return prototype_root / "data" / "ppm.db"

    # -----------------------------
    # Users
    # -----------------------------
    def upsert_user(self, user: User) -> None:
        self.conn.execute(
            """
            INSERT INTO users (id, name, email, role, clearance)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name,
              email=excluded.email,
              role=excluded.role,
              clearance=excluded.clearance;
            """,
            (user.id, user.name, user.email, user.role, user.clearance),
        )
        self.conn.commit()

    def list_users(self) -> list[User]:
        rows = self.conn.execute(
            "SELECT id, name, email, role, clearance FROM users ORDER BY name;"
        ).fetchall()
        return [
            User(
                id=r["id"],
                name=r["name"],
                email=r["email"],
                role=r["role"],
                clearance=r["clearance"],
            )
            for r in rows
        ]

    def get_user(self, user_id: str) -> User | None:
        r = self.conn.execute(
            "SELECT id, name, email, role, clearance FROM users WHERE id=?;",
            (user_id,),
        ).fetchone()
        if not r:
            return None
        return User(
            id=r["id"], name=r["name"], email=r["email"], role=r["role"], clearance=r["clearance"]
        )

    # -----------------------------
    # Entities
    # -----------------------------
    def create_entity(
        self,
        *,
        type: str,
        title: str,
        status: str,
        classification: str,
        data: dict[str, Any] | None = None,
        entity_id: str | None = None,
    ) -> Entity:
        eid = entity_id or new_id(type)
        now = now_iso()
        payload = data or {}
        self.conn.execute(
            """
            INSERT INTO entities (id, type, title, status, classification, data_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (eid, type, title, status, classification, json_dumps_compact(payload), now, now),
        )
        self.conn.commit()
        return self.get_entity(eid, include_data=True)  # type: ignore

    def update_entity(
        self,
        entity_id: str,
        *,
        title: str | None = None,
        status: str | None = None,
        classification: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Entity:
        existing = self.get_entity(entity_id, include_data=True)
        if not existing:
            raise KeyError(f"Entity not found: {entity_id}")
        new_title = title if title is not None else existing.title
        new_status = status if status is not None else existing.status
        new_class = classification if classification is not None else existing.classification
        new_data = data if data is not None else existing.data
        now = now_iso()
        self.conn.execute(
            """
            UPDATE entities
            SET title=?, status=?, classification=?, data_json=?, updated_at=?
            WHERE id=?;
            """,
            (new_title, new_status, new_class, json_dumps_compact(new_data), now, entity_id),
        )
        self.conn.commit()
        updated = self.get_entity(entity_id, include_data=True)
        assert updated is not None
        return updated

    def get_entity(self, entity_id: str, *, include_data: bool = True) -> Entity | None:
        r = self.conn.execute(
            "SELECT id, type, title, status, classification, data_json, created_at, updated_at FROM entities WHERE id=?;",
            (entity_id,),
        ).fetchone()
        if not r:
            return None
        data = json_loads(r["data_json"]) if include_data else {}
        return Entity(
            id=r["id"],
            type=r["type"],
            title=r["title"],
            status=r["status"],
            classification=r["classification"],
            data=data or {},
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )

    def list_entities(self, *, type: str | None = None, limit: int = 200) -> list[Entity]:
        if type:
            rows = self.conn.execute(
                "SELECT id, type, title, status, classification, data_json, created_at, updated_at FROM entities WHERE type=? ORDER BY updated_at DESC LIMIT ?;",
                (type, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id, type, title, status, classification, data_json, created_at, updated_at FROM entities ORDER BY updated_at DESC LIMIT ?;",
                (limit,),
            ).fetchall()
        out: list[Entity] = []
        for r in rows:
            out.append(
                Entity(
                    id=r["id"],
                    type=r["type"],
                    title=r["title"],
                    status=r["status"],
                    classification=r["classification"],
                    data=json_loads(r["data_json"]) or {},
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
            )
        return out

    def delete_entity(self, entity_id: str) -> None:
        self.conn.execute("DELETE FROM entities WHERE id=?;", (entity_id,))
        self.conn.execute(
            "DELETE FROM relations WHERE from_id=? OR to_id=?;", (entity_id, entity_id)
        )
        self.conn.commit()

    # -----------------------------
    # Relations
    # -----------------------------
    def link(self, from_id: str, to_id: str, relation_type: str) -> None:
        rid = new_id("rel")
        now = now_iso()
        self.conn.execute(
            """
            INSERT OR IGNORE INTO relations (id, from_id, to_id, relation_type, created_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (rid, from_id, to_id, relation_type, now),
        )
        self.conn.commit()

    def list_links(self, entity_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id, from_id, to_id, relation_type, created_at
            FROM relations
            WHERE from_id=? OR to_id=?
            ORDER BY created_at DESC;
            """,
            (entity_id, entity_id),
        ).fetchall()
        return [dict(r) for r in rows]

    # -----------------------------
    # Events / audit
    # -----------------------------
    def log_event(
        self,
        *,
        actor: str,
        event_type: str,
        entity_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        eid = new_id("evt")
        ts = now_iso()
        self.conn.execute(
            """
            INSERT INTO events (id, timestamp, actor, event_type, entity_id, details_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (eid, ts, actor, event_type, entity_id, json_dumps_compact(details or {})),
        )
        self.conn.commit()

    def list_events(
        self, *, limit: int = 200, entity_id: str | None = None
    ) -> list[dict[str, Any]]:
        if entity_id:
            rows = self.conn.execute(
                "SELECT id, timestamp, actor, event_type, entity_id, details_json FROM events WHERE entity_id=? ORDER BY timestamp DESC LIMIT ?;",
                (entity_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id, timestamp, actor, event_type, entity_id, details_json FROM events ORDER BY timestamp DESC LIMIT ?;",
                (limit,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["details"] = json_loads(r["details_json"]) or {}
            out.append(d)
        return out

    # -----------------------------
    # Agent runs
    # -----------------------------
    def record_agent_run(
        self,
        *,
        agent_id: int,
        agent_name: str,
        entity_id: str | None,
        actor: str,
        started_at: str,
        ended_at: str,
        status: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        log: str,
    ) -> None:
        rid = new_id("run")
        self.conn.execute(
            """
            INSERT INTO agent_runs (id, agent_id, agent_name, entity_id, actor, started_at, ended_at, status, input_json, output_json, log)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                rid,
                agent_id,
                agent_name,
                entity_id,
                actor,
                started_at,
                ended_at,
                status,
                json_dumps_compact(inputs),
                json_dumps_compact(outputs),
                log,
            ),
        )
        self.conn.commit()

    def list_agent_runs(
        self, *, limit: int = 200, entity_id: str | None = None
    ) -> list[dict[str, Any]]:
        if entity_id:
            rows = self.conn.execute(
                "SELECT * FROM agent_runs WHERE entity_id=? ORDER BY started_at DESC LIMIT ?;",
                (entity_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT ?;",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # -----------------------------
    # Workflows
    # -----------------------------
    def upsert_workflow_def(
        self,
        *,
        wf_id: str,
        name: str,
        version: str,
        entity_type: str,
        json_def: str,
        active: bool = True,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO workflow_defs (id, name, version, entity_type, json_def, active)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name,
              version=excluded.version,
              entity_type=excluded.entity_type,
              json_def=excluded.json_def,
              active=excluded.active;
            """,
            (wf_id, name, version, entity_type, json_def, 1 if active else 0),
        )
        self.conn.commit()

    def list_workflow_defs(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, name, version, entity_type, json_def, active FROM workflow_defs ORDER BY name;"
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["def"] = json_loads(r["json_def"]) or {}
            out.append(d)
        return out

    def get_workflow_def(self, wf_id: str) -> dict[str, Any] | None:
        r = self.conn.execute(
            "SELECT id, name, version, entity_type, json_def, active FROM workflow_defs WHERE id=?;",
            (wf_id,),
        ).fetchone()
        if not r:
            return None
        d = dict(r)
        d["def"] = json_loads(r["json_def"]) or {}
        return d

    def create_workflow_instance(
        self,
        *,
        def_id: str,
        entity_id: str,
        status: str,
        current_step_id: str | None,
        context: dict[str, Any],
    ) -> str:
        iid = new_id("wfi")
        now = now_iso()
        self.conn.execute(
            """
            INSERT INTO workflow_instances (id, def_id, entity_id, status, current_step_id, context_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                iid,
                def_id,
                entity_id,
                status,
                current_step_id,
                json_dumps_compact(context),
                now,
                now,
            ),
        )
        self.conn.commit()
        return iid

    def update_workflow_instance(
        self,
        instance_id: str,
        *,
        status: str | None = None,
        current_step_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        existing = self.get_workflow_instance(instance_id)
        if not existing:
            raise KeyError(f"Workflow instance not found: {instance_id}")
        new_status = status if status is not None else existing["status"]
        new_step = current_step_id if current_step_id is not None else existing["current_step_id"]
        new_ctx = context if context is not None else existing["context"]
        now = now_iso()
        self.conn.execute(
            """
            UPDATE workflow_instances
            SET status=?, current_step_id=?, context_json=?, updated_at=?
            WHERE id=?;
            """,
            (new_status, new_step, json_dumps_compact(new_ctx), now, instance_id),
        )
        self.conn.commit()

    def get_workflow_instance(self, instance_id: str) -> dict[str, Any] | None:
        r = self.conn.execute(
            "SELECT * FROM workflow_instances WHERE id=?;", (instance_id,)
        ).fetchone()
        if not r:
            return None
        d = dict(r)
        d["context"] = json_loads(r["context_json"]) or {}
        return d

    def list_workflow_instances(self, *, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM workflow_instances ORDER BY updated_at DESC LIMIT ?;", (limit,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["context"] = json_loads(r["context_json"]) or {}
            out.append(d)
        return out

    # -----------------------------
    # Connectors
    # -----------------------------
    def upsert_connector(
        self,
        *,
        connector_id: str,
        system_name: str,
        category: str | None,
        status: str,
        config: dict[str, Any],
        last_sync: str | None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO connectors (id, system_name, category, status, config_json, last_sync)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              system_name=excluded.system_name,
              category=excluded.category,
              status=excluded.status,
              config_json=excluded.config_json,
              last_sync=excluded.last_sync;
            """,
            (connector_id, system_name, category, status, json_dumps_compact(config), last_sync),
        )
        self.conn.commit()

    def list_connectors(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM connectors ORDER BY system_name;").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["config"] = json_loads(r["config_json"]) or {}
            out.append(d)
        return out

    # -----------------------------
    # Metrics
    # -----------------------------
    def add_metric(self, metric_name: str, value: float) -> None:
        mid = new_id("m")
        ts = now_iso()
        self.conn.execute(
            "INSERT INTO metrics (id, metric_name, value, timestamp) VALUES (?, ?, ?, ?);",
            (mid, metric_name, value, ts),
        )
        self.conn.commit()

    def latest_metrics(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT metric_name, value, timestamp FROM metrics ORDER BY timestamp DESC LIMIT ?;",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

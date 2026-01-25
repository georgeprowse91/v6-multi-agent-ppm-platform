from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional


def get_conn(db_file: Path) -> sqlite3.Connection:
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Make foreign keys enforceable
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


SCHEMA_STATEMENTS: Iterable[str] = [
    # Users
    """
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      email TEXT,
      role TEXT NOT NULL,
      clearance TEXT NOT NULL
    );
    """,
    # Flexible entity store (JSON payload)
    """
    CREATE TABLE IF NOT EXISTS entities (
      id TEXT PRIMARY KEY,
      type TEXT NOT NULL,
      title TEXT NOT NULL,
      status TEXT NOT NULL,
      classification TEXT NOT NULL,
      data_json TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
    """,
    # Relations between entities (e.g., intake -> business_case, project -> risk)
    """
    CREATE TABLE IF NOT EXISTS relations (
      id TEXT PRIMARY KEY,
      from_id TEXT NOT NULL,
      to_id TEXT NOT NULL,
      relation_type TEXT NOT NULL,
      created_at TEXT NOT NULL,
      UNIQUE(from_id, to_id, relation_type)
    );
    """,
    # Events / audit
    """
    CREATE TABLE IF NOT EXISTS events (
      id TEXT PRIMARY KEY,
      timestamp TEXT NOT NULL,
      actor TEXT NOT NULL,
      event_type TEXT NOT NULL,
      entity_id TEXT,
      details_json TEXT
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_id);
    """,
    # Agent runs for traceability
    """
    CREATE TABLE IF NOT EXISTS agent_runs (
      id TEXT PRIMARY KEY,
      agent_id INTEGER,
      agent_name TEXT,
      entity_id TEXT,
      actor TEXT,
      started_at TEXT,
      ended_at TEXT,
      status TEXT,
      input_json TEXT,
      output_json TEXT,
      log TEXT
    );
    """,
    # Workflow definitions + instances
    """
    CREATE TABLE IF NOT EXISTS workflow_defs (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      version TEXT NOT NULL,
      entity_type TEXT NOT NULL,
      json_def TEXT NOT NULL,
      active INTEGER NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_instances (
      id TEXT PRIMARY KEY,
      def_id TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      status TEXT NOT NULL,
      current_step_id TEXT,
      context_json TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    """,
    # Connector registry (simulated)
    """
    CREATE TABLE IF NOT EXISTS connectors (
      id TEXT PRIMARY KEY,
      system_name TEXT NOT NULL,
      category TEXT,
      status TEXT NOT NULL,
      config_json TEXT NOT NULL,
      last_sync TEXT
    );
    """,
    # Basic metrics
    """
    CREATE TABLE IF NOT EXISTS metrics (
      id TEXT PRIMARY KEY,
      metric_name TEXT NOT NULL,
      value REAL,
      timestamp TEXT NOT NULL
    );
    """,
]


def init_db(conn: sqlite3.Connection) -> None:
    for stmt in SCHEMA_STATEMENTS:
        conn.execute(stmt)
    conn.commit()

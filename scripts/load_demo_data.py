#!/usr/bin/env python3
"""Load demo data into PostgreSQL and Cosmos DB.

Environment variables:
- DEMO_DATA_DIR (optional): path to demo JSON files (default: data/demo)
- POSTGRES_DSN (optional): psycopg DSN for PostgreSQL
- COSMOS_DB_CONNECTION_STRING (optional): Azure Cosmos DB connection string
- COSMOS_DB_DATABASE (optional): Cosmos DB database name (default: ppm-demo)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

ENTITY_FILES = [
    "portfolios",
    "programs",
    "projects",
    "tasks",
    "resources",
    "budgets",
    "epics",
    "sprints",
    "risks",
    "issues",
    "vendors",
    "contracts",
    "policies",
    "approvals",
]


def _load_entities(data_dir: Path) -> dict[str, list[dict[str, Any]]]:
    entities: dict[str, list[dict[str, Any]]] = {}
    for name in ENTITY_FILES:
        path = data_dir / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing demo data file: {path}")
        entities[name] = json.loads(path.read_text(encoding="utf-8"))
    return entities


def _load_postgres(entities: dict[str, list[dict[str, Any]]], dsn: str) -> None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS demo_entities (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    PRIMARY KEY (entity_type, entity_id)
                )
                """
            )
            cur.execute("DELETE FROM demo_entities")
            for entity_type, rows in entities.items():
                for row in rows:
                    entity_id = str(row.get("id") or row.get("name") or row.get("title"))
                    cur.execute(
                        """
                        INSERT INTO demo_entities (entity_type, entity_id, payload)
                        VALUES (%s, %s, %s::jsonb)
                        """,
                        (entity_type, entity_id, json.dumps(row)),
                    )
        conn.commit()


def _load_cosmos(
    entities: dict[str, list[dict[str, Any]]],
    connection_string: str,
    database_name: str,
) -> None:
    from azure.cosmos import CosmosClient, PartitionKey

    client = CosmosClient.from_connection_string(connection_string)
    database = client.create_database_if_not_exists(database_name)

    for entity_type, rows in entities.items():
        container = database.create_container_if_not_exists(
            id=f"demo_{entity_type}",
            partition_key=PartitionKey(path="/tenant_id"),
        )

        # Clear current demo documents in container.
        docs = list(
            container.query_items(
                query="SELECT c.id, c.tenant_id FROM c",
                enable_cross_partition_query=True,
            )
        )
        for doc in docs:
            container.delete_item(item=doc["id"], partition_key=doc.get("tenant_id", "tenant-demo"))

        for row in rows:
            payload = dict(row)
            payload.setdefault("id", f"{entity_type}-{abs(hash(json.dumps(row, sort_keys=True))) % 1000000}")
            payload.setdefault("tenant_id", "tenant-demo")
            container.create_item(payload)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    repo_root = Path(__file__).resolve().parents[1]
    data_dir = Path(os.getenv("DEMO_DATA_DIR", repo_root / "data" / "demo"))

    logging.info("Loading demo data files from %s", data_dir)
    entities = _load_entities(data_dir)
    logging.info("Loaded %s entity files", len(entities))

    postgres_dsn = os.getenv("POSTGRES_DSN")
    if postgres_dsn:
        _load_postgres(entities, postgres_dsn)
        logging.info("PostgreSQL demo data refresh complete")
    else:
        logging.info("POSTGRES_DSN not set; skipping PostgreSQL load")

    cosmos_connection_string = os.getenv("COSMOS_DB_CONNECTION_STRING")
    if cosmos_connection_string:
        cosmos_database = os.getenv("COSMOS_DB_DATABASE", "ppm-demo")
        _load_cosmos(entities, cosmos_connection_string, cosmos_database)
        logging.info("Cosmos DB demo data refresh complete")
    else:
        logging.info("COSMOS_DB_CONNECTION_STRING not set; skipping Cosmos DB load")

    logging.info("Demo data load completed successfully")


if __name__ == "__main__":
    main()

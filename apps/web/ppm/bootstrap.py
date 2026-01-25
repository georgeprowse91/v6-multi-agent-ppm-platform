from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .store import Store
from .security import User
from .utils import json_dumps_compact, new_id


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bootstrap() -> Store:
    """Initialise the store, seed example data (once), and load workflow templates."""
    store = Store(Store.default_db_file())

    prototype_root = Path(__file__).resolve().parents[1]
    data_dir = prototype_root / "data"

    # Seed users + sample entities only if database is empty
    if len(store.list_users()) == 0:
        seed_path = data_dir / "seed.json"
        if seed_path.exists():
            seed = _read_json(seed_path)

            # Users
            for u in seed.get("users", []):
                store.upsert_user(
                    User(
                        id=u["id"],
                        name=u["name"],
                        email=u.get("email"),
                        role=u["role"],
                        clearance=u.get("clearance", "Internal"),
                    )
                )

            # Seed entities by type
            type_map = {
                "portfolios": "portfolio",
                "resources": "resource",
                "policies": "policy",
            }
            for key, etype in type_map.items():
                for e in seed.get(key, []):
                    store.create_entity(
                        type=etype,
                        title=e["title"],
                        status=e.get("status", "Active"),
                        classification=e.get("classification", "Internal"),
                        data=e.get("data", {}),
                    )

            # Seed connectors
            for c in seed.get("connectors", []):
                cid = new_id("conn")
                store.upsert_connector(
                    connector_id=cid,
                    system_name=c["title"],
                    category=c.get("data", {}).get("category"),
                    status=c.get("status", "Planned"),
                    config=c.get("data", {}),
                    last_sync=None,
                )

            store.log_event(actor="system", event_type="seed_completed", details={"seed": "seed.json"})

    # Load workflow templates into workflow_defs
    wf_dir = data_dir / "workflows"
    if wf_dir.exists():
        for wf_file in sorted(wf_dir.glob("*.json")):
            wf = _read_json(wf_file)
            store.upsert_workflow_def(
                wf_id=wf["id"],
                name=wf["name"],
                version=wf.get("version", "1.0"),
                entity_type=wf.get("entity_type", "unknown"),
                json_def=json_dumps_compact(wf),
                active=True,
            )

    return store

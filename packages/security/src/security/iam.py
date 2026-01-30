from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"groups": {}, "roles": []}
    return yaml.safe_load(path.read_text()) or {"groups": {}, "roles": []}


def map_groups_to_roles(claims: dict[str, Any]) -> list[str]:
    mapping_path = Path(
        os.getenv("IAM_ROLE_MAPPING_PATH", "config/iam/role-mapping.yaml")
    )
    mapping = _load_mapping(mapping_path)
    group_map = mapping.get("groups", {})
    group_ids = claims.get("groups") or []
    roles: list[str] = []
    for group_id in group_ids:
        mapped = group_map.get(group_id)
        if mapped:
            if isinstance(mapped, list):
                roles.extend(mapped)
            else:
                roles.append(str(mapped))
    return sorted(set(roles))

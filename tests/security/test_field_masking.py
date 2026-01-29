from __future__ import annotations

from pathlib import Path

import yaml

from api.middleware.security import _mask_fields


def test_field_masking_nested_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    field_cfg = yaml.safe_load((repo_root / "config" / "rbac" / "field-level.yaml").read_text())
    payload = {
        "project": {
            "id": "proj-1",
            "financials": {"approval_limit": 125000},
        }
    }

    masked = _mask_fields(payload, field_cfg, roles=["analyst"])
    assert masked["project"]["financials"]["approval_limit"] == "REDACTED"

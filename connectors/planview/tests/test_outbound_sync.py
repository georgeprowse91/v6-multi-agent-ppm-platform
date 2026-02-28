from __future__ import annotations

import ast
from pathlib import Path

from integrations.connectors.planview.src.mappers import map_to_planview


def test_send_to_external_system_maps_payload_shape_for_mcp_and_non_mcp() -> None:
    records = [{"id": "p1", "name": "Project", "status": "open", "start_date": "2024-01-01"}]
    mapped_payload = map_to_planview(records)

    assert mapped_payload == [
        {
            "externalId": "p1",
            "name": "Project",
            "lifecycleState": "active",
            "startDate": "2024-01-01",
            "financials": {"currency": "USD"},
        }
    ]


def test_send_to_external_system_uses_single_mapped_payload_contract() -> None:
    source = Path("integrations/connectors/planview/src/main.py").read_text()
    tree = ast.parse(source)

    send_fn = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "send_to_external_system"
    )
    fn_source = ast.get_source_segment(source, send_fn) or ""

    assert "mapped_payload = map_to_planview(records)" in fn_source
    assert "for payload in mapped_payload" in fn_source
    assert "connector.create_work_item(payload)" in fn_source
    assert "mapped_payload" in fn_source and "Outbound payload for Planview tenant" in fn_source

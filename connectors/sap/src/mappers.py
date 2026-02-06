from __future__ import annotations

from typing import Any, Iterable


def map_to_sap(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert canonical PPM records into SAP-compatible payloads.

    Args:
        records: Canonical records produced by the mapping engine.

    Returns:
        A list of dictionaries formatted for the SAP API.

    Note:
        This placeholder implementation returns the records unchanged.
        Update this function with SAP-specific mapping rules when available.
    """
    return list(records)

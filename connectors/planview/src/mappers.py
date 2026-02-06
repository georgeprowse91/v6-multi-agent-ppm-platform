from __future__ import annotations

from typing import Any, Iterable


def map_to_planview(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert canonical PPM records into Planview-compatible payloads.

    Args:
        records: Canonical records produced by the mapping engine.

    Returns:
        A list of dictionaries formatted for the Planview API.

    Note:
        This placeholder implementation returns the records unchanged.
        Update this function with Planview-specific mapping rules when available.
    """
    return list(records)

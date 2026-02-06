from __future__ import annotations

from typing import Any, Iterable


def map_to_clarity(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert canonical PPM records into Clarity-compatible payloads.

    Args:
        records: Canonical records produced by the mapping engine.

    Returns:
        A list of dictionaries formatted for the Clarity API.

    Note:
        This placeholder implementation returns the records unchanged.
        Update this function with Clarity-specific mapping rules when available.
    """
    return list(records)

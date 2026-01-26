from __future__ import annotations

import logging
from datetime import datetime, timezone

from audit_storage import get_worm_storage

logger = logging.getLogger("audit-retention")
logging.basicConfig(level=logging.INFO)


def run_retention_enforcement(now: datetime | None = None) -> int:
    storage = get_worm_storage()
    deleted = storage.prune_expired(now=now or datetime.now(timezone.utc))
    logger.info("audit_retention_prune", extra={"deleted": deleted})
    return deleted


if __name__ == "__main__":
    run_retention_enforcement()

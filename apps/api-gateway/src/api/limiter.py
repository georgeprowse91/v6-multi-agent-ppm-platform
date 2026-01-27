from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

rate_limit_default = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
rate_limit_storage = os.getenv("RATE_LIMIT_STORAGE", "memory://")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[rate_limit_default],
    storage_uri=rate_limit_storage,
)

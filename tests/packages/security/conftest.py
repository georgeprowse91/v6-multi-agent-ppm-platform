"""Conftest for security package tests: freeze time at FIXED_NOW so JWT expiry assertions work."""

from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest

# Must match FIXED_NOW in test_auth_package.py
_FIXED_NOW = 1_700_000_000
_FIXED_DT = datetime.datetime.fromtimestamp(_FIXED_NOW, tz=datetime.timezone.utc)


class _FrozenDatetime(datetime.datetime):
    """datetime subclass that returns a fixed instant from now()."""

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        if tz is not None:
            return _FIXED_DT.astimezone(tz)
        return _FIXED_DT.replace(tzinfo=None)

    @classmethod
    def utcnow(cls):  # type: ignore[override]
        return _FIXED_DT.replace(tzinfo=None)


@pytest.fixture(autouse=True)
def _freeze_time():
    """Patch PyJWT's datetime so JWT exp checks use FIXED_NOW instead of wall-clock time."""
    with patch("jwt.api_jwt.datetime", _FrozenDatetime):
        yield

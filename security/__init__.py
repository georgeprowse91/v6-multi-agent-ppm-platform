"""Compatibility package exposing ``packages/security/src/security`` as ``security``."""

from pathlib import Path

_pkg_dir = Path(__file__).resolve().parents[1] / "packages" / "security" / "src" / "security"
if _pkg_dir.is_dir():
    __path__.append(str(_pkg_dir))

from packages.security.src.security import *  # noqa: F401,F403,E402

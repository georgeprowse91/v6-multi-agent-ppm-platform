"""Regulatory Compliance connector test fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "connectors" / "sdk" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "connectors" / "regulatory_compliance" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "packages" / "common" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "vendor" / "stubs"))
sys.path.insert(0, str(_REPO_ROOT / "vendor"))
sys.path.insert(0, str(_REPO_ROOT))

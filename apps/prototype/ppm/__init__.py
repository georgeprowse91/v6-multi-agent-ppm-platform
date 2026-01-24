"""Agentic PPM Platform Prototype backend package.

This package is intentionally small and dependency-light.
It provides:
- a flexible SQLite entity store
- lightweight RBAC and data classification checks
- agent stubs (one per documented agent)
- a simple workflow engine with approval gates
"""

from .bootstrap import bootstrap

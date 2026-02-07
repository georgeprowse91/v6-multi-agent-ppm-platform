"""
Pytest configuration for Jira connector tests.
"""

import sys
from pathlib import Path

# Add connector paths to sys.path
REPO_ROOT = Path(__file__).resolve().parents[4]
CONNECTOR_SDK_PATH = REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"
JIRA_CONNECTOR_PATH = REPO_ROOT / "integrations" / "connectors" / "jira" / "src"

for path in (CONNECTOR_SDK_PATH, JIRA_CONNECTOR_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

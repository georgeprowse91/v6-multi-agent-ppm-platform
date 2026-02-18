from __future__ import annotations

import pytest

from api.document_session_store import resolve_document_session_storage


def test_document_session_storage_dev_allows_default_sqlite() -> None:
    selection = resolve_document_session_storage(environment="development", configured_db_path=None)

    assert str(selection.db_path).endswith("data/documents/sessions.db")
    assert selection.source == "default"
    assert selection.durability_mode == "file-backed"


def test_document_session_storage_staging_rejects_default_sqlite() -> None:
    with pytest.raises(ValueError, match="DOCUMENT_SESSION_DB_PATH"):
        resolve_document_session_storage(environment="staging", configured_db_path=None)

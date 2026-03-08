from __future__ import annotations

import sys
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

DOC_SRC = Path(__file__).resolve().parents[1] / "src"
REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_SRC = REPO_ROOT / "packages" / "security" / "src"
for path in (DOC_SRC, SECURITY_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import main  # noqa: E402
from document_storage import DocumentStore  # noqa: E402


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DOCUMENT_DB_PATH", str(tmp_path / "documents.db"))
    monkeypatch.setenv("DOCUMENT_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))
    main.store = None
    return TestClient(main.app)


def test_create_document_with_pii_is_denied_when_policy_blocks(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    response = client.post(
        "/documents",
        json={
            "name": "pii-doc",
            "content": "Card 4111 1111 1111 1111",
            "classification": "confidential",
            "retention_days": 90,
            "metadata": {},
        },
    )
    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["details"]["reasons"]


def test_create_document_with_minor_pii_is_advisory_and_returns_advisories(
    tmp_path, monkeypatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    response = client.post(
        "/documents",
        json={
            "name": "email-doc",
            "content": "Contact me at user@example.com",
            "classification": "internal",
            "retention_days": 90,
            "metadata": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert any("DLP email" in advisory for advisory in payload["advisories"])


def test_stored_db_does_not_contain_plaintext_content(tmp_path: Path) -> None:
    db_path = tmp_path / "documents.db"
    key = Fernet.generate_key().decode("utf-8")
    store = DocumentStore(db_path, encryption_key=key)
    store.create_document(
        tenant_id="tenant-1",
        name="secret-doc",
        classification="restricted",
        retention_days=90,
        content="Top secret value 4111 1111 1111 1111",
        metadata={},
    )
    raw = db_path.read_bytes()
    assert b"Top secret value" not in raw


def test_get_document_returns_decrypted_content(tmp_path: Path) -> None:
    db_path = tmp_path / "documents.db"
    key = Fernet.generate_key().decode("utf-8")
    store = DocumentStore(db_path, encryption_key=key)
    created = store.create_document(
        tenant_id="tenant-1",
        name="secret-doc",
        classification="restricted",
        retention_days=90,
        content="Sensitive content",
        metadata={},
    )
    fetched = store.get_document("tenant-1", created.document_id)
    assert fetched is not None
    assert fetched.content == "Sensitive content"

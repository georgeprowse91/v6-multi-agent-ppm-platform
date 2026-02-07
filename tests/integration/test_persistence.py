from sqlalchemy.orm import Session

from integrations.services.integration.persistence import Base, InMemoryDocumentStore, SqlRepository, create_sql_engine


def test_sql_repository_persists_risk_record():
    engine = create_sql_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = SqlRepository(session)
        risk = repo.add_risk("Late delivery", "high", "Add contingency")
    assert risk.title == "Late delivery"
    assert risk.severity == "high"


def test_in_memory_document_store_upserts():
    store = InMemoryDocumentStore()
    stored = store.upsert("risk-1", {"title": "Late delivery"})
    assert stored["id"] == "risk-1"
    assert store.read("risk-1")["title"] == "Late delivery"


def test_sql_repository_persists_compliance_and_process_logs():
    engine = create_sql_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = SqlRepository(session)
        evidence = repo.add_compliance_evidence(
            "audit", "evidence/42", "collected", "signed by QA"
        )
        log = repo.add_process_log("release", "ok", "release completed")
    assert evidence.reference == "evidence/42"
    assert log.process_name == "release"

from sqlalchemy.orm import Session

from services.integration.persistence import (
    Base,
    InMemoryDocumentStore,
    RiskRecord,
    SqlRepository,
    create_sql_engine,
)


def test_sql_repository_persists_risk_record():
    engine = create_sql_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = SqlRepository(session)
        risk = repo.add_risk("Late delivery", "high", "Add contingency")

        fetched = session.query(RiskRecord).filter_by(id=risk.id).one()

    assert fetched.title == "Late delivery"
    assert fetched.severity == "high"


def test_in_memory_document_store_upserts():
    store = InMemoryDocumentStore()
    stored = store.upsert("risk-1", {"title": "Late delivery"})
    assert stored["id"] == "risk-1"
    assert store.read("risk-1")["title"] == "Late delivery"

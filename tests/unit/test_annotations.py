"""Tests for collaborative editing annotations (Enhancement 8).

Tests cover SQLite-backed persistence, dismiss/apply operations,
in-memory fallback, and rule-based suggestion generation.
"""

from __future__ import annotations

import asyncio

import pytest
from annotations import Annotation, AnnotationStore, generate_suggestions


@pytest.fixture
def store(tmp_path):
    """Create an annotation store with a temporary SQLite database."""
    db_path = tmp_path / "test_annotations.db"
    return AnnotationStore(db_path=db_path, persist=True)


@pytest.fixture
def memory_store():
    """Create an in-memory-only annotation store."""
    return AnnotationStore(persist=False)


def test_create_annotation(store):
    ann = Annotation(
        agent_id="risk-agent",
        agent_name="Risk Management",
        block_id="b1",
        content="Consider adding risk mitigation",
        annotation_type="suggestion",
    )
    created = store.create_annotation("session-1", ann)
    assert created.session_id == "session-1"
    assert created.annotation_id.startswith("ann-")


def test_list_annotations(store):
    store.create_annotation("s1", Annotation(content="a"))
    store.create_annotation("s1", Annotation(content="b"))
    store.create_annotation("s2", Annotation(content="c"))
    assert len(store.list_annotations("s1")) == 2
    assert len(store.list_annotations("s2")) == 1


def test_dismiss_annotation(store):
    ann = store.create_annotation("s1", Annotation(content="dismiss me"))
    store.dismiss_annotation(ann.annotation_id)
    active = store.list_annotations("s1", active_only=True)
    assert len(active) == 0
    all_anns = store.list_annotations("s1", active_only=False)
    assert len(all_anns) == 1
    assert all_anns[0].dismissed is True


def test_apply_annotation(store):
    ann = store.create_annotation("s1", Annotation(content="apply me"))
    result = store.apply_annotation(ann.annotation_id)
    assert result is not None
    assert result.applied is True


def test_dismiss_nonexistent(store):
    assert store.dismiss_annotation("nope") is None


def test_memory_fallback(memory_store):
    """Test that in-memory fallback works when persistence is disabled."""
    ann = memory_store.create_annotation("s1", Annotation(content="in-memory"))
    assert ann.session_id == "s1"
    assert len(memory_store.list_annotations("s1")) == 1
    memory_store.dismiss_annotation(ann.annotation_id)
    assert len(memory_store.list_annotations("s1", active_only=True)) == 0


def test_persistence_across_instances(tmp_path):
    """Verify annotations persist across store instances."""
    db_path = tmp_path / "persist_test.db"
    store1 = AnnotationStore(db_path=db_path, persist=True)
    store1.create_annotation("s1", Annotation(content="persistent"))
    del store1

    store2 = AnnotationStore(db_path=db_path, persist=True)
    anns = store2.list_annotations("s1")
    assert len(anns) == 1
    assert anns[0].content == "persistent"


def test_generate_suggestions_risk():
    """Test rule-based suggestion generation for risk content."""
    suggestions = asyncio.run(
        generate_suggestions("s1", "b1", "There is a significant risk of schedule delay")
    )
    assert len(suggestions) >= 1
    agent_ids = {s.agent_id for s in suggestions}
    assert "risk-management" in agent_ids or "schedule-planning" in agent_ids


def test_generate_suggestions_budget():
    """Test rule-based suggestion generation for financial content."""
    suggestions = asyncio.run(
        generate_suggestions("s1", "b1", "The project budget has exceeded cost estimates")
    )
    assert len(suggestions) >= 1
    agent_ids = {s.agent_id for s in suggestions}
    assert "financial-management" in agent_ids


def test_generate_suggestions_long_content():
    """Test that long content triggers knowledge agent."""
    long_content = "This is a detailed analysis. " * 50
    suggestions = asyncio.run(
        generate_suggestions("s1", "b1", long_content)
    )
    agent_ids = {s.agent_id for s in suggestions}
    assert "knowledge-management" in agent_ids


# --- Error path and edge case tests ---


def test_create_multiple_annotations_same_session(store):
    """Multiple annotations in the same session should all be retrievable."""
    for i in range(10):
        store.create_annotation("multi-s", Annotation(content=f"note-{i}", block_id=f"b{i}"))
    anns = store.list_annotations("multi-s")
    assert len(anns) == 10


def test_list_annotations_empty_session(store):
    """Listing annotations for a session with none should return empty list."""
    assert store.list_annotations("nonexistent-session") == []


def test_dismiss_already_dismissed(store):
    """Dismissing an already-dismissed annotation should be idempotent."""
    ann = store.create_annotation("s1", Annotation(content="double dismiss"))
    store.dismiss_annotation(ann.annotation_id)
    result = store.dismiss_annotation(ann.annotation_id)
    assert result is not None
    assert result.dismissed is True


def test_apply_already_applied(store):
    """Applying an already-applied annotation should be idempotent."""
    ann = store.create_annotation("s1", Annotation(content="double apply"))
    store.apply_annotation(ann.annotation_id)
    result = store.apply_annotation(ann.annotation_id)
    assert result is not None
    assert result.applied is True


def test_apply_nonexistent(store):
    """Applying a nonexistent annotation should return None."""
    assert store.apply_annotation("nope-id") is None


def test_annotation_ids_unique(store):
    """Each annotation should get a unique ID."""
    ids = set()
    for _ in range(20):
        ann = store.create_annotation("s-unique", Annotation(content="test"))
        assert ann.annotation_id not in ids
        ids.add(ann.annotation_id)


def test_annotation_session_isolation(store):
    """Annotations from different sessions should not leak."""
    store.create_annotation("session-a", Annotation(content="a"))
    store.create_annotation("session-b", Annotation(content="b"))
    assert len(store.list_annotations("session-a")) == 1
    assert len(store.list_annotations("session-b")) == 1


def test_dismissed_not_in_active_list(store):
    """Dismissed annotations should not appear in active_only=True listing."""
    store.create_annotation("s1", Annotation(content="keep"))
    ann2 = store.create_annotation("s1", Annotation(content="dismiss"))
    store.dismiss_annotation(ann2.annotation_id)
    active = store.list_annotations("s1", active_only=True)
    assert len(active) == 1
    assert active[0].content == "keep"


def test_memory_fallback_apply(memory_store):
    """In-memory fallback should support apply operations."""
    ann = memory_store.create_annotation("s1", Annotation(content="test"))
    result = memory_store.apply_annotation(ann.annotation_id)
    assert result is not None
    assert result.applied is True


def test_generate_suggestions_compliance():
    """Compliance keywords should trigger compliance agent."""
    suggestions = asyncio.run(
        generate_suggestions("s1", "b1", "We need GDPR compliance for the data migration")
    )
    agent_ids = {s.agent_id for s in suggestions}
    assert "compliance-governance" in agent_ids


def test_generate_suggestions_schedule():
    """Deadline keywords should trigger schedule agent."""
    suggestions = asyncio.run(
        generate_suggestions("s1", "b1", "The milestone deadline is overdue by two weeks")
    )
    agent_ids = {s.agent_id for s in suggestions}
    assert "schedule-planning" in agent_ids


def test_generate_suggestions_no_match():
    """Content with no keyword matches should return empty suggestions."""
    suggestions = asyncio.run(
        generate_suggestions("s1", "b1", "Hello world")
    )
    assert isinstance(suggestions, list)

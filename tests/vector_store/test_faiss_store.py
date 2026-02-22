import time

import numpy as np
from packages.vector_store.faiss_store import FaissVectorStore


def _unit(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def test_add_and_search_embeddings_returns_expected_neighbor() -> None:
    store = FaissVectorStore(dimension=4, num_shards=1, batch_size=2)
    embeddings = np.asarray(
        [
            _unit(np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32)),
            _unit(np.asarray([0.0, 1.0, 0.0, 0.0], dtype=np.float32)),
            _unit(np.asarray([0.8, 0.2, 0.0, 0.0], dtype=np.float32)),
        ],
        dtype=np.float32,
    )
    ids = ["doc-a", "doc-b", "doc-c"]

    store.add_embeddings(embeddings, ids)
    store.flush()

    results = store.search(_unit(np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32)), top_k=2)

    assert results
    assert results[0][0] in {"doc-a", "doc-c"}
    assert len(results) == 2


def test_search_across_multiple_shards() -> None:
    store = FaissVectorStore(dimension=8, num_shards=4, batch_size=4)
    rng = np.random.default_rng(7)
    embeddings = rng.random((24, 8), dtype=np.float32)
    embeddings = np.asarray([_unit(row) for row in embeddings], dtype=np.float32)
    ids = [f"doc-{idx}" for idx in range(24)]

    store.add_embeddings(embeddings, ids)
    store.flush()

    query = embeddings[13]
    results = store.search(query, top_k=5)

    assert len(results) == 5
    assert any(doc_id == "doc-13" for doc_id, _ in results)


def test_ttl_eviction_and_delete() -> None:
    store = FaissVectorStore(dimension=4, num_shards=2, embedding_ttl_seconds=1, batch_size=8)
    embeddings = np.asarray(
        [
            _unit(np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32)),
            _unit(np.asarray([0.0, 1.0, 0.0, 0.0], dtype=np.float32)),
        ],
        dtype=np.float32,
    )
    ids = ["live", "expire"]

    store.add_embeddings(embeddings, ids)
    store.flush()
    store.delete(["live"])
    assert all(doc_id != "live" for doc_id, _ in store.search(embeddings[0], top_k=5))

    time.sleep(1.05)
    assert store.search(embeddings[1], top_k=5) == []


def test_large_dummy_dataset_query_latency() -> None:
    dimension = 64
    rows = 5000
    rng = np.random.default_rng(42)
    embeddings = rng.random((rows, dimension), dtype=np.float32)
    embeddings = np.asarray([_unit(row) for row in embeddings], dtype=np.float32)
    ids = [f"item-{idx}" for idx in range(rows)]

    store = FaissVectorStore(
        dimension=dimension, num_shards=8, batch_size=256, nlist=128, nprobe=16
    )
    store.add_embeddings(embeddings, ids)
    store.flush()

    start = time.perf_counter()
    results = store.search(embeddings[rows // 3], top_k=10)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(results) == 10
    assert elapsed_ms < 150.0

from __future__ import annotations

import hashlib
import math
import time
from collections import OrderedDict
from dataclasses import dataclass

import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    faiss = None


@dataclass
class _ShardState:
    ids: list[str]
    vectors: np.ndarray


class FaissVectorStore:
    """Shard-aware vector store with optional FAISS acceleration and TTL-aware eviction."""

    def __init__(
        self,
        *,
        dimension: int,
        num_shards: int = 1,
        nlist: int = 64,
        nprobe: int = 10,
        batch_size: int = 128,
        cache_size: int = 256,
        cache_ttl_seconds: int = 30,
        embedding_ttl_seconds: int | None = None,
    ) -> None:
        self.dimension = dimension
        self.num_shards = max(1, num_shards)
        self.nlist = max(1, nlist)
        self.nprobe = max(1, nprobe)
        self.batch_size = max(1, batch_size)
        self.cache_size = max(1, cache_size)
        self.cache_ttl_seconds = max(1, cache_ttl_seconds)
        self.embedding_ttl_seconds = embedding_ttl_seconds

        self._id_to_shard: dict[str, int] = {}
        self._id_to_row: dict[str, int] = {}
        self._id_to_expiry: dict[str, float] = {}
        self._pending_by_shard: dict[int, list[tuple[str, np.ndarray]]] = {
            shard: [] for shard in range(self.num_shards)
        }
        self._cache: OrderedDict[str, tuple[float, list[tuple[str, float]]]] = OrderedDict()

        self._shards: dict[int, _ShardState] = {
            shard: _ShardState(ids=[], vectors=np.empty((0, self.dimension), dtype=np.float32))
            for shard in range(self.num_shards)
        }
        self._faiss_indexes: dict[int, object] = {}

    def add_embeddings(self, embeddings: np.ndarray, ids: list[str]) -> None:
        if len(ids) == 0:
            return
        vectors = np.asarray(embeddings, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Embeddings must be 2D with dimension {self.dimension}; got {vectors.shape}."
            )
        if vectors.shape[0] != len(ids):
            raise ValueError("Length of ids must match number of embeddings.")

        self._purge_expired()
        now = time.time()

        for row, doc_id in enumerate(ids):
            shard = self._shard_for_id(doc_id)
            vector = vectors[row]
            self._pending_by_shard[shard].append((doc_id, vector))
            if self.embedding_ttl_seconds is not None:
                self._id_to_expiry[doc_id] = now + self.embedding_ttl_seconds
            if len(self._pending_by_shard[shard]) >= self.batch_size:
                self._flush_shard(shard)

        self._invalidate_cache()

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        if top_k <= 0:
            return []

        self._purge_expired()
        self._flush_all_pending()

        query_vector = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        if query_vector.shape[1] != self.dimension:
            raise ValueError(
                f"Query embedding dimension must be {self.dimension}; got {query_vector.shape[1]}."
            )

        cache_key = self._make_cache_key(query_vector[0], top_k)
        cached = self._cache.get(cache_key)
        if cached is not None and cached[0] > time.time():
            return cached[1]

        scored: list[tuple[str, float]] = []
        per_shard_k = min(top_k, max(1, math.ceil(top_k / self.num_shards) + 2))
        for shard in range(self.num_shards):
            scored.extend(self._search_shard(shard, query_vector, per_shard_k))

        scored.sort(key=lambda item: item[1], reverse=True)
        deduped: list[tuple[str, float]] = []
        seen: set[str] = set()
        for doc_id, score in scored:
            if doc_id in seen:
                continue
            seen.add(doc_id)
            deduped.append((doc_id, score))
            if len(deduped) >= top_k:
                break

        self._cache_set(cache_key, deduped)
        return deduped

    def search_many(
        self, query_embeddings: np.ndarray, top_k: int
    ) -> list[list[tuple[str, float]]]:
        """Batch search helper for improved throughput on multi-query workloads."""
        vectors = np.asarray(query_embeddings, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Query embeddings must be 2D with dimension {self.dimension}; got {vectors.shape}."
            )
        return [self.search(vectors[row], top_k=top_k) for row in range(vectors.shape[0])]

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return

        self._flush_all_pending()
        touched_shards: set[int] = set()
        for doc_id in ids:
            shard = self._id_to_shard.get(doc_id)
            if shard is None:
                continue
            row = self._id_to_row.get(doc_id)
            if row is None:
                continue
            state = self._shards[shard]
            if 0 <= row < len(state.ids) and state.ids[row] == doc_id:
                state.ids.pop(row)
                state.vectors = np.delete(state.vectors, row, axis=0)
                touched_shards.add(shard)
            self._id_to_shard.pop(doc_id, None)
            self._id_to_row.pop(doc_id, None)
            self._id_to_expiry.pop(doc_id, None)

        for shard in touched_shards:
            self._rebuild_row_map(shard)
            self._rebuild_faiss_index(shard)
        if touched_shards:
            self._invalidate_cache()

    def flush(self) -> None:
        self._flush_all_pending()

    def _flush_all_pending(self) -> None:
        for shard in range(self.num_shards):
            if self._pending_by_shard[shard]:
                self._flush_shard(shard)

    def _flush_shard(self, shard: int) -> None:
        pending = self._pending_by_shard[shard]
        if not pending:
            return
        state = self._shards[shard]
        ids, vectors = zip(*pending, strict=False)
        pending_vectors = np.vstack(vectors).astype(np.float32)

        for doc_id in ids:
            if doc_id in self._id_to_shard:
                self.delete([doc_id])
            state.ids.append(doc_id)
            self._id_to_shard[doc_id] = shard
            self._id_to_row[doc_id] = len(state.ids) - 1

        if state.vectors.size == 0:
            state.vectors = pending_vectors
        else:
            state.vectors = np.vstack([state.vectors, pending_vectors])

        self._pending_by_shard[shard] = []
        self._rebuild_faiss_index(shard)

    def _search_shard(
        self, shard: int, query_vector: np.ndarray, top_k: int
    ) -> list[tuple[str, float]]:
        state = self._shards[shard]
        if state.vectors.size == 0:
            return []

        if faiss is not None and shard in self._faiss_indexes:
            index = self._faiss_indexes[shard]
            distances, indices = index.search(query_vector, min(top_k, len(state.ids)))
            results: list[tuple[str, float]] = []
            for dist, idx in zip(distances[0], indices[0], strict=False):
                if idx < 0:
                    continue
                doc_id = state.ids[int(idx)]
                score = float(1.0 / (1.0 + dist))
                results.append((doc_id, score))
            return results

        similarities = _cosine_similarity_matrix(query_vector, state.vectors)[0]
        if similarities.size == 0:
            return []
        top_count = min(top_k, similarities.size)
        top_indices = np.argpartition(similarities, -top_count)[-top_count:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
        return [(state.ids[int(idx)], float(similarities[int(idx)])) for idx in top_indices]

    def _rebuild_faiss_index(self, shard: int) -> None:
        if faiss is None:
            return
        state = self._shards[shard]
        if state.vectors.shape[0] == 0:
            self._faiss_indexes.pop(shard, None)
            return

        quantizer = faiss.IndexFlatL2(self.dimension)
        nlist = min(self.nlist, max(1, state.vectors.shape[0] // 4))
        index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist, faiss.METRIC_L2)
        if not index.is_trained:
            index.train(state.vectors)
        index.add(state.vectors)
        index.nprobe = min(self.nprobe, nlist)
        self._faiss_indexes[shard] = index

    def _purge_expired(self) -> None:
        if self.embedding_ttl_seconds is None:
            return
        now = time.time()
        expired = [doc_id for doc_id, expiry in self._id_to_expiry.items() if expiry <= now]
        if expired:
            self.delete(expired)

    def _cache_set(self, key: str, value: list[tuple[str, float]]) -> None:
        expiry = time.time() + self.cache_ttl_seconds
        self._cache[key] = (expiry, value)
        self._cache.move_to_end(key)
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    def _invalidate_cache(self) -> None:
        self._cache.clear()

    def _make_cache_key(self, query_embedding: np.ndarray, top_k: int) -> str:
        rounded = np.round(query_embedding, 5)
        digest = hashlib.sha256(rounded.tobytes()).hexdigest()
        return f"{digest}:{top_k}"

    def _rebuild_row_map(self, shard: int) -> None:
        state = self._shards[shard]
        for idx, doc_id in enumerate(state.ids):
            self._id_to_row[doc_id] = idx

    def _shard_for_id(self, doc_id: str) -> int:
        return hash(doc_id) % self.num_shards


def _cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = np.linalg.norm(b, axis=1, keepdims=True)
    a_norm[a_norm == 0] = 1.0
    b_norm[b_norm == 0] = 1.0
    return (a / a_norm) @ (b / b_norm).T

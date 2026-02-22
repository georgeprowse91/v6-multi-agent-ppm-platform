# Vector Store Scalability Design

## Overview

The platform now supports a shard-aware FAISS-backed vector store implementation for high-volume duplicate detection and semantic retrieval workflows. The implementation centers on `FaissVectorStore` in `packages/vector_store/faiss_store.py` and a higher-level adapter `FaissBackedVectorSearchIndex` used by portfolio agents.

## Architecture

- **Storage primitive**: `FaissVectorStore`.
  - Supports configurable sharding (`num_shards`) to spread vectors across partitions.
  - Uses `IndexIVFFlat` when `faiss` is available; otherwise falls back to a NumPy cosine similarity path.
  - Exposes `add_embeddings`, `search`, `search_many`, `delete`, and `flush`.
- **Agent integration adapter**: `FaissBackedVectorSearchIndex` in `agents/common/integration_services.py`.
  - Preserves existing `add` and `search` style used by agents.
  - Loads index tuning from `ops/ops/config/vector_store.yaml`.
  - Stores metadata separately and merges metadata into search results.

## Scalability controls

### Sharding

- Each document ID is deterministically mapped to a shard.
- Search fans out across shards and merges top results.
- Recommended scale-up path:
  1. Increase `num_shards`.
  2. Increase `nlist`.
  3. Tune `nprobe` to balance recall vs latency.

### Batching

- `add_embeddings` stages vectors in per-shard queues.
- Flush occurs automatically at `batch_size` and can be forced via `flush()`.
- `search_many` provides multi-query batch execution.

### Caching

- Internal LRU-style cache stores recent query results with TTL (`cache_ttl_seconds`) and bounded size (`cache_size`).
- Agent adapter also keeps a small query cache (`query_cache_size`) to avoid recomputation of repeated queries.

### TTL-based retention

- Embeddings can be configured with `embedding_ttl_seconds`.
- Expired vectors are purged during add/search operations.
- Use shorter TTL for high-churn domains and longer TTL for historical benchmarking workloads.

## Operational tuning

Configure index settings in `ops/ops/config/vector_store.yaml`:

- `num_shards`: parallelism and index partitioning.
- `nlist`: coarse cluster count for IVF.
- `nprobe`: cluster probes per query.
- `batch_size`: write throughput vs index freshness.
- `cache_size` and `cache_ttl_seconds`: query cache behavior.
- `embedding_ttl_seconds`: lifecycle cleanup window.

## Current agent usage

- Demand & Intake Agent (`agent-04`) uses the `demand_intake` index profile.
- Business Case & Investment Agent (`agent-05`) uses the `business_case` index profile.

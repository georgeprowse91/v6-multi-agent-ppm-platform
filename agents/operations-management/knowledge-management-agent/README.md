# Knowledge Management Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Knowledge Management Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Ingest documents from users, agent outputs, and connected repositories (e.g., Confluence, SharePoint, Git).
- Normalize metadata, enforce schema validation, and manage document versions/retention.
- Generate summaries, tags, entity extraction, taxonomy labeling, and knowledge graph links.
- Enforce access controls and classification rules for retrieval.
- Provide search (keyword + semantic) and recommendation services.
- Persist knowledge artifacts (lessons learned, decisions, risks) for reuse.

The Knowledge Management agent operates as the system of record for document metadata, summaries, and knowledge graph relationships (projects, programs, risks, decisions, lessons learned). It does **not** originate stakeholder communications or analytics KPI narratives; it provides curated knowledge artifacts to those agents when requested.

### Inputs
- **User or agent requests** with an `action` (e.g., `upload_document`, `ingest_sources`, `search_documents`).
- **Documents** with `title`, `content`, and metadata (project/program/portfolio IDs, classification, permissions).
- **Ingestion sources** for repositories (Confluence, SharePoint, Git).
- **Access context** for authorization checks (`user_id`, `roles`, `attributes`).

### Outputs
- **Document IDs, versions, and classification labels** upon ingestion.
- **Search results** with relevance scores and excerpts.
- **Summaries, extracted entities, and knowledge graph links.**
- **Lessons learned IDs and categorized knowledge artifacts.**
- **Access logs and version history** for audit/traceability.

### Decision responsibilities
- Document acceptance/rejection based on schema validation and required metadata.
- Auto-classification, tagging, and taxonomy placement.
- Access control enforcement (RBAC/ABAC).
- Knowledge graph relationship creation (document → project/program/portfolio, risk, decision).
- Whether to trigger asynchronous summarization/entity extraction tasks.

### Must / must-not behaviors
- **Must** validate required fields and schema before persisting documents.
- **Must** preserve version history on updates and emit knowledge ingestion events.
- **Must** enforce access controls before returning content.
- **Must** record knowledge graph relationships for decisions/risks where detected.
- **Must** maintain traceability metadata (source, timestamps, ownership).
- **Must not** bypass access controls for non-public documents.
- **Must not** modify or delete documents without versioning or audit trail.
- **Must not** send stakeholder-facing messages or create analytics KPIs.
- **Must not** store documents without classification and ownership metadata.

## Overlap & handoff boundaries

### Stakeholder Communications
- **Overlap risk**: meeting minutes, decisions, and summaries may be both knowledge artifacts and communication payloads.
- **Boundary**: The Knowledge Management agent **stores and indexes** the documents; the Stakeholder Communications agent **delivers** communications. The Knowledge Management agent provides curated artifacts (summaries, decision logs, lessons learned) to the Stakeholder Communications agent for distribution. The Stakeholder Communications agent should not modify source knowledge content; it may annotate distribution metadata in its own system.

### Analytics Insights
- **Overlap risk**: both domains handle insights, reports, and narrative summaries.
- **Boundary**: The Knowledge Management agent **curates content** and provides retrieval/search; the Analytics Insights agent **computes KPIs, predictive insights, and dashboards**. The Analytics Insights agent requests document corpora or knowledge artifacts (lessons learned, decision/risk history) from the Knowledge Management agent to enrich models and narratives. The Knowledge Management agent should not compute KPIs or analytics metrics.

## Functional gaps / inconsistencies & alignment needs

- **Prompt alignment**: current system prompts should explicitly differentiate document curation vs. communications and analytics responsibilities to avoid duplicate summaries.
- **Tooling alignment**: connectors (Confluence/SharePoint/Git) should share a common ingestion contract with analytics ETL pipelines to prevent double-ingestion.
- **Template alignment**: knowledge summaries and decision logs should follow a shared template so the Stakeholder Communications agent can reuse them verbatim in outbound comms.
- **UI alignment**: knowledge search UI should expose access context and classification filters to avoid unauthorized disclosure.
- **Knowledge graph alignment**: risk/decision extraction should include consistent identifiers so analytics agents can join knowledge artifacts with KPI datasets.

## Checkpoint: knowledge lifecycle map

1. **Capture**: user upload, agent output ingestion, or repository sync.
2. **Validate**: schema enforcement, metadata normalization, classification tagging.
3. **Enrich**: summaries, entities, taxonomy labels, knowledge graph links.
4. **Store**: versioned persistence + audit log; emit ingestion event.
5. **Retrieve**: keyword/semantic search with access control.
6. **Share**: handoff curated artifacts to the Stakeholder Communications agent / analytics agents.
7. **Review**: annotations, approvals, retention and lifecycle updates.
8. **Retire**: archive or delete with audit trail and compliance checks.

## What's inside

- [src](/agents/operations-management/knowledge-management-agent/src): Implementation source for this component.
- [tests](/agents/operations-management/knowledge-management-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/operations-management/knowledge-management-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name knowledge-management-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/knowledge-management-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Semantic search and summarization

The Knowledge Management agent supports embedding-powered semantic search and concise result summaries:

- Embeddings are generated with `sentence-transformers` (default model: `all-MiniLM-L6-v2`) with automatic fallback to local embeddings if the model is unavailable.
- Vector search can run in-memory or via the FAISS-backed vector store (`vector_store_backend`).
- Search responses include per-document metadata (`title`, `date`, `relevance_score`) and an LLM-generated concise summary for each hit.
- Summaries are prompt-driven via the prompt registry (`prompts/knowledge-agent/summary_prompt_v1.md`) and inputs are sanitized for prompt injection before summarization.

#### Configuration knobs

Agent-level defaults are defined in `ops/config/agents/knowledge_agent.yaml`:

- `embeddings.model`: sentence-transformers model name.
- `embeddings.dimensions`: expected embedding dimension.
- `embeddings.vector_store_backend`: `in_memory` or `faiss`.
- `search.semantic_result_limit`: top-N semantic results to return.
- `summarization.summary_token_limit`: max summary tokens per document.
- `summarization.summary_prompt_agent_id`: prompt registry key for summarization prompt selection.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.

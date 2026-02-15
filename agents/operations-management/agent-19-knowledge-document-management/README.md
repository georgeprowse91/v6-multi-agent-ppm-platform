# Agent 19: Knowledge Document Management Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 19: Knowledge Document Management. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

Agent 19 owns the knowledge/document lifecycle across the portfolio: ingesting, classifying, indexing, governing access, and serving documents/knowledge artifacts for downstream agents and humans. The agent operates as the system of record for document metadata, summaries, and knowledge graph relationships (projects, programs, risks, decisions, lessons learned). It does **not** originate stakeholder communications or analytics KPI narratives; it provides curated knowledge artifacts to those agents when requested.

### In-scope responsibilities

- Ingest documents from users, agent outputs, and connected repositories (e.g., Confluence, SharePoint, Git).  
- Normalize metadata, enforce schema validation, and manage document versions/retention.  
- Generate summaries, tags, entity extraction, taxonomy labeling, and knowledge graph links.  
- Enforce access controls and classification rules for retrieval.  
- Provide search (keyword + semantic) and recommendation services.  
- Persist knowledge artifacts (lessons learned, decisions, risks) for reuse.

### Out-of-scope responsibilities

- Sending emails/messages or scheduling meetings (belongs to Agent 21).  
- Computing portfolio KPIs, predictive analytics, or dashboards (belongs to analytics agents).  
- Executing workflow automations outside knowledge capture or storage.

## Inputs and outputs

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

## Decision responsibilities

Agent 19 is the decision-maker for:

- Document acceptance/rejection based on schema validation and required metadata.  
- Auto-classification, tagging, and taxonomy placement.  
- Access control enforcement (RBAC/ABAC).  
- Knowledge graph relationship creation (document → project/program/portfolio, risk, decision).  
- Whether to trigger asynchronous summarization/entity extraction tasks.  

Agent 19 **does not** decide:

- Who receives communications or how/when to notify stakeholders (Agent 21).  
- KPI definitions, analytics model outputs, or dashboard narrative framing (Analytics agents).  

## Must / must-not behaviors

**Must**

- Validate required fields and schema before persisting documents.  
- Preserve version history on updates and emit knowledge ingestion events.  
- Enforce access controls before returning content.  
- Record knowledge graph relationships for decisions/risks where detected.  
- Maintain traceability metadata (source, timestamps, ownership).  

**Must not**

- Bypass access controls for non-public documents.  
- Modify or delete documents without versioning or audit trail.  
- Send stakeholder-facing messages or create analytics KPIs.  
- Store documents without classification and ownership metadata.  

## Overlap analysis and handoff boundaries

### Agent 21: Stakeholder Comms

**Potential overlap:** Meeting minutes, decisions, and summaries may be both knowledge artifacts and communication payloads.  
**Boundary:** Agent 19 **stores and indexes** the documents; Agent 21 **delivers** communications.  
**Handoff:** Agent 19 provides curated artifacts (summaries, decision logs, lessons learned) to Agent 21 for distribution. Agent 21 should not modify source knowledge content; it may annotate distribution metadata in its own system.

### Analytics agent (Agent 22)

**Potential overlap:** Both domains handle insights, reports, and narrative summaries.  
**Boundary:** Agent 19 **curates content** and provides retrieval/search; Agent 22 **computes KPIs, predictive insights, and dashboards**.  
**Handoff:** Agent 22 requests document corpora or knowledge artifacts (lessons learned, decision/risk history) from Agent 19 to enrich models and narratives. Agent 19 should not compute KPIs or analytics metrics.

## Functional gaps / inconsistencies to resolve

- **Prompt alignment:** Current system prompts should explicitly differentiate document curation vs. communications and analytics responsibilities to avoid duplicate summaries.  
- **Tooling alignment:** Connectors (Confluence/SharePoint/Git) should share a common ingestion contract with analytics ETL pipelines to prevent double-ingestion.  
- **Template alignment:** Knowledge summaries and decision logs should follow a shared template so Agent 21 can reuse them verbatim in outbound comms.  
- **UI alignment:** Knowledge search UI should expose access context and classification filters to avoid unauthorized disclosure.  
- **Knowledge graph alignment:** Risk/decision extraction should include consistent identifiers so analytics agents can join knowledge artifacts with KPI datasets.

## Knowledge lifecycle map (checkpoint)

1. **Capture**: user upload, agent output ingestion, or repository sync.  
2. **Validate**: schema enforcement, metadata normalization, classification tagging.  
3. **Enrich**: summaries, entities, taxonomy labels, knowledge graph links.  
4. **Store**: versioned persistence + audit log; emit ingestion event.  
5. **Retrieve**: keyword/semantic search with access control.  
6. **Share**: handoff curated artifacts to Agent 21 / analytics agents.  
7. **Review**: annotations, approvals, retention and lifecycle updates.  
8. **Retire**: archive or delete with audit trail and compliance checks.

## What's inside

- [agents/operations-management/agent-19-knowledge-document-management/src](/agents/operations-management/agent-19-knowledge-document-management/src): Implementation source for this component.
- [agents/operations-management/agent-19-knowledge-document-management/tests](/agents/operations-management/agent-19-knowledge-document-management/tests): Test suites and fixtures.
- [agents/operations-management/agent-19-knowledge-document-management/Dockerfile](/agents/operations-management/agent-19-knowledge-document-management/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-19-knowledge-document-management --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/agent-19-knowledge-document-management/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.


## Semantic search and summarization

Agent 19 now supports embedding-powered semantic search and concise result summaries:

- Embeddings are generated with `sentence-transformers` (default model: `all-MiniLM-L6-v2`) with automatic fallback to local embeddings if the model is unavailable.
- Vector search can run in-memory or via the FAISS-backed vector store (`vector_store_backend`).
- Search responses include per-document metadata (`title`, `date`, `relevance_score`) and an LLM-generated concise summary for each hit.
- Summaries are prompt-driven via the prompt registry (`prompts/knowledge-agent/summary_prompt_v1.md`) and inputs are sanitized for prompt injection before summarization.

### Configuration knobs

Agent-level defaults are defined in `ops/config/agents/knowledge_agent.yaml`:

- `embeddings.model`: sentence-transformers model name.
- `embeddings.dimensions`: expected embedding dimension.
- `embeddings.vector_store_backend`: `in_memory` or `faiss`.
- `search.semantic_result_limit`: top-N semantic results to return.
- `summarization.summary_token_limit`: max summary tokens per document.
- `summarization.summary_prompt_agent_id`: prompt registry key for summarization prompt selection.

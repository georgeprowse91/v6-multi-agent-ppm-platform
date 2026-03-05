# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Enterprise authentication with SSO/MFA, role-based access control enforcement, and audit-ready access controls.
- IoT connector support for asset telemetry in project workflows.
- Vendor procurement workflow enhancements with configurable approvals and bid comparison views.
- Updated UX across portfolio and lifecycle dashboards for improved navigation.
- MCP connector release readiness checklist and environment-specific deployment guidance.

### Changed
- Product, marketing, success metrics, and solution index documentation aligned to delivered capabilities.
- `docs/README.md` updated to include all documentation subdirectories (`change-management/`, `dependencies/`, `testing/`, `ui/`) and all top-level key files.
- `services/README.md` updated to include `memory_service` (conversation context persistence) and `scope_baseline` (scope baseline development artefact; not a deployed microservice).
- `packages/README.md` updated to include `connectors` (shared connector SDK utilities), `design-tokens` (design system tokens), `feedback` (agent feedback capture), and `vector_store` (FAISS-backed vector store) packages.
- `apps/README.md` updated to include `demo_streamlit` (Streamlit-based interactive demo application).
- `docs/solution-index.md` connector inventory expanded to reflect all 38 implemented connectors across PPM, ERP, GRC, HR, collaboration, and communications domains.
- `docs/data/data-model.md` updated to include `Scenario` as a canonical entity and added platform schemas section (`agent_config`, `agent-run`).
- `docs/architecture/system-context.md` external systems list expanded to cover all integration domains (GRC, HR, CRM, IoT, Communications).
- `docs/agents/README.md` agent configuration file paths corrected from `config/agents/` to `ops/config/agents/`.

## [1.0.0] - 2026-01-27
### Added
- Production evidence pack, deterministic quickstart runbook, and demo scenario assets.
- Structured validation for core orchestration agents and deterministic mock LLM routing.
- Response orchestration caching, bounded concurrency, retries, and circuit-breaker hooks.
- Coverage-gated CI quickstart smoke scenario.

### Changed
- Updated project metadata to production/stable release classification.

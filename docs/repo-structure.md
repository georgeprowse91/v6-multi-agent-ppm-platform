# Repository Structure and Root Declutter Plan

This document captures the phase-1 declutter baseline and guardrails.

## Current root inventory

Top-level entries at the time of this phase:

- `.devcontainer/`
- `.dockerignore`
- `.env.demo`
- `.env.example`
- `.git/`
- `.gitattributes`
- `.github/`
- `.gitignore`
- `.pre-commit-config.yaml`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `LICENSE`
- `Makefile`
- `README.md`
- `SECURITY.md`
- `agents/`
- `alembic.ini`
- `apps/`
- `config/`
- `data/`
- `design-system/`
- `docker-compose.test.yml`
- `docker-compose.yml`
- `docs/`
- `examples/`
- `infra/`
- `integrations/`
- `jinja2/`
- `jsonschema/`
- `mkdocs.yml`
- `node_modules/`
- `ops/`
- `packages/`
- `pnpm-lock.yaml`
- `pnpm-workspace.yaml`
- `policies/`
- `prompt_registry.py`
- `prompts/`
- `pydantic_settings.py`
- `pyproject.toml`
- `requirements-dev.in`
- `requirements-dev.txt`
- `requirements.in`
- `requirements.txt`
- `runtime_flags.py`
- `scripts/`
- `services/`
- `tests/`

## Top-level classification

### MUST_STAY_ROOT

- `.gitignore`, `.pre-commit-config.yaml`, `README.md`, `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md`
- `pyproject.toml`, `pnpm-workspace.yaml`, `pnpm-lock.yaml`, `Makefile`
- `docker-compose.yml`, `docker-compose.test.yml`, `mkdocs.yml`, `alembic.ini`, `.env.example`
- Root compatibility modules (current): `prompt_registry.py`, `runtime_flags.py`, `pydantic_settings.py`

### CAN_MOVE_NOW

- No file moves executed in this phase. We intentionally focused on documentation and machine guardrails.

### CAN_MOVE_WITH_MIGRATION

- `prompt_registry.py`, `runtime_flags.py`, `pydantic_settings.py` (all have live imports across services/agents).
- requirements duplication (`requirements*.txt` + `pyproject.toml`) can be consolidated only after a staged packaging migration that preserves existing install paths.

### SHOULD_DELETE_OR_CONSOLIDATE

- `node_modules/` should remain ignored/generated and never be tracked as a durable root artifact.
- `jinja2/` and `jsonschema/` are candidates for consolidation under a clearer domain path in a future phase after validating references.

## Dependency-impact checks (phase 1 findings)

- Direct imports exist for root modules:
  - `from prompt_registry import ...`
  - `from runtime_flags import ...`
  - lookups/import checks for `pydantic_settings`
- Multiple runtime/docs/tooling references target root config filenames such as `.env.example`, `pyproject.toml`, and `alembic.ini`.
- Tests and workflow scripts rely on root discovery conventions (e.g., loading `alembic.ini` by default path).

Conclusion: risky module/config relocations are deferred.

## Target declutter structure (steady state)

- Root: only governance, manifests, and toolchain discovery files.
- Domain content: grouped under `apps/`, `agents/`, `services/`, `integrations/`, `ops/`, `docs/`, etc.
- Compatibility shims: if needed during migration, keep minimal root forwarding modules with deprecation notices.

## Phased roadmap

### Phase 1 (this PR): docs + guardrails

- Add root file policy.
- Add root allowlist checker script.
- Wire a make target for local/CI usage.
- Add targeted tests for the checker.

### Phase 2: reference mapping + migration prep

- Build a complete import/reference matrix for compatibility modules.
- Decide destination packages and compatibility shim strategy.
- Add deprecation timeline and communication notes.

### Phase 3: module relocation with compatibility

- Move root compatibility modules into scoped packages.
- Add root shim modules or path adapters.
- Run full test and lint suites.

### Phase 4: dependency manifest consolidation

- Propose single-source dependency authority while preserving `pip install -r requirements*.txt` workflows during transition.
- Migrate CI and docs incrementally.

# Root File Policy

This policy defines what is allowed at repository root and why.

## Policy goals

- Keep root navigable for contributors and automation.
- Preserve discovery conventions required by core tooling.
- Route non-root-sensitive artifacts into domain folders (`docs/`, `ops/`, `scripts/`, etc.).

## Root allowlist categories

### 1) Root-sensitive toolchain files (must stay)

These are resolved by default by package managers, build tools, CI, or local workflows:

- `pyproject.toml`
- `pnpm-workspace.yaml`
- `pnpm-lock.yaml`
- `Makefile`
- `docker-compose.yml`
- `docker-compose.test.yml`
- `mkdocs.yml`
- `alembic.ini`
- `.pre-commit-config.yaml`
- `.gitignore`
- `README.md`
- `CONTRIBUTING.md`
- `LICENSE`
- `SECURITY.md`
- `.env.example`

### 2) Root-level compatibility modules (temporary allowlist)

The following modules currently have direct imports from multiple packages and services and remain at root until a dedicated import migration phase is complete:

- `prompt_registry.py`
- `runtime_flags.py`
- `pydantic_settings.py`

### 3) Approved root directories

Top-level domain directories are allowed for monorepo organization:

- `agents/`, `apps/`, `config/`, `data/`, `design-system/`, `docs/`, `examples/`, `infra/`,
  `integrations/`, `ops/`, `packages/`, `policies/`, `prompts/`, `scripts/`, `services/`, `tests/`

## Change process for root additions

1. Prefer placing new files in an existing domain folder.
2. If a new root file is required, document rationale in `docs/repo-structure.md`.
3. Update `ops/tools/check_root_layout.py` allowlist in the same PR.
4. Ensure `make check-root-layout` passes.

## Explicit non-goals (phase 1)

- No risky relocations of compatibility modules.
- No breaking changes to Python or Node install/discovery flows.

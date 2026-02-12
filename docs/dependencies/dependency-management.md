# Dependency Management Policy

## Dependency groups and update cadence

- **Runtime dependencies**: defined in `pyproject.toml` under `project.dependencies`; reviewed and updated **monthly**.
- **Dev tooling dependencies**: defined in `pyproject.toml` under `project.optional-dependencies.dev`; reviewed and updated **bi-weekly**.
- **Test dependencies**: defined in `pyproject.toml` under `project.optional-dependencies.test`; reviewed and updated **bi-weekly**.

## Version constraint strategy

- Use bounded ranges (`>=x,<y`) in `pyproject.toml` to avoid open-ended upgrades.
- Keep major versions pinned by upper bounds unless compatibility verification is complete.

## Lockfiles and reproducibility

- This repository does not currently use a Python lockfile (`poetry.lock`, `pdm.lock`, etc.).
- Reproducibility is maintained through pinned `requirements.txt` and `requirements-dev.txt`, regenerated alongside dependency updates.

## Known constraints

- `azure-ai-anomalydetector` remains on 3.x because v4 is not generally available.
- `langchain` remains constrained to 0.3.x pending migration work for breaking changes in 1.x.
- `sqlalchemy` remains `<2.1` until async engine migration validation is complete.

## CI enforcement

- `.github/workflows/dependency-audit.yml` runs:
  - `pip-audit` against runtime and development requirements.
  - A compatibility smoke test matrix on Python 3.11 and 3.12.
  - `pip check` and an outdated-package report artifact for visibility.

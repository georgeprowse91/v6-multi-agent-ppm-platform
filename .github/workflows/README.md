# GitHub Actions Workflows

## Purpose

Define the CI/CD, security, and compliance pipelines that validate and release the Multi-Agent PPM Platform. The workflows here mirror the checks invoked by `make check` and the release pipeline described in `docs/architecture/`.

## What's inside

- [ci.yml](/.github/workflows/ci.yml): Core CI pipeline (lint, tests, docs checks).
- [pr.yml](/.github/workflows/pr.yml): Pull request validation and gating checks.
- [cd.yml](/.github/workflows/cd.yml): Release/promotion flow for tagged builds.
- [contract-tests.yml](/.github/workflows/contract-tests.yml): Contract test runs for shared schemas.
- [e2e-tests.yml](/.github/workflows/e2e-tests.yml): End-to-end workflow validations.
- [test-dependency-matrix.md](/docs/testing/test-dependency-matrix.md): Test matrix and dependency profile documentation for CI.
- [security-scan.yml](/.github/workflows/security-scan.yml): Security scanning and policy enforcement.
- [secret-scan.yml](/.github/workflows/secret-scan.yml): Secret scanning checks.
- [iac-scan.yml](/.github/workflows/iac-scan.yml): Infrastructure-as-code scan (when enabled).

## How it's used

These workflows run automatically on pull requests, pushes to protected branches, or release tags. They are the authoritative record of required checks before deployment.

## How to run / develop / test

Most checks can be run locally before opening a PR (see also `docs/testing/test-dependency-matrix.md` for dependency sets):

```bash
make lint
make test
make check-links
make check-placeholders
```

## Configuration

Workflow secrets and tokens are configured in GitHub repository settings (Actions → Secrets and variables). Environment-specific values should match the settings in `.env.example` and the infra configuration.

## Troubleshooting

- A workflow fails due to missing secrets: verify the GitHub Actions secrets and environment variables are set.
- CI steps fail locally but pass in CI: ensure you are using Python 3.11+ and have installed dev dependencies.
- Job timeouts: check workflow job time limits and reduce any long-running steps.

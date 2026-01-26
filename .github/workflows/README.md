# GitHub Actions Workflows

## Purpose
This folder contains the CI/CD automation for the Multi-Agent PPM platform, including build,
release, security scanning, and contract testing workflows.

## Responsibilities
- Define CI jobs for linting, testing, and security checks.
- Orchestrate release and deployment pipelines.
- Provide clear workflow ownership for platform automation.

## Folder structure
```
.github/workflows/
├── ci.yml
├── cd.yml
├── pr.yml
├── security-scan.yml
├── contract-tests.yml
└── README.md
```

## Conventions
- Workflow files are named by intent (`ci.yml`, `cd.yml`, `release.yml`).
- Each workflow must include `name`, `on`, and `jobs` keys.
- Workflow changes should include an update to this README when new pipelines are added.

## How to add a new workflow
1. Create a new `.yml` file in `.github/workflows/`.
2. Define the `name`, `on`, and `jobs` sections.
3. Update this README with the new workflow file.
4. Validate with the script below.

## How to validate/test
```bash
python scripts/validate-github-workflows.py
```

## Example
```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
```

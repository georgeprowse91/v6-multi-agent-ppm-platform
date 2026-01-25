# Code Generation

This folder contains the OpenAPI validation and contract summary generation used by
the API gateway and downstream packages.

## What it does

* Validates `docs/api/openapi.yaml` is parseable and contains `openapi`, `info`, and `paths`.
* Writes deterministic summaries to `apps/api-gateway/openapi/`:
  * `openapi_summary.json`: version, title, and path metadata.
  * `openapi_paths.txt`: newline-delimited list of HTTP paths.

## Usage

```bash
python -m tools.codegen.run
```

To override defaults, edit `tools/codegen/codegen_config.yaml`.

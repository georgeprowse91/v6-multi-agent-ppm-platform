# OpenAPI Artifacts

This folder stores generated OpenAPI summaries produced by the repo tooling. The source
specification lives in `docs/api/openapi.yaml`.

## Generate the summaries

```bash
python -m tools.codegen.run
```

Expected output:

```text
Generated OpenAPI summary at apps/api-gateway/openapi.
```

## What gets generated

After running the command, you should see:

- `openapi_summary.json` with API version metadata and counts
- `openapi_paths.txt` with one path per line

Example `openapi_summary.json` (truncated):

```json
{
  "openapi": "3.0.3",
  "title": "Multi-Agent PPM Platform API",
  "version": "0.1.0",
  "path_count": 8,
  "operation_count": 12
}
```

# Code Generation

OpenAPI validation and deterministic summary generation used by the API gateway.

## Quickstart

```bash
python -m tools.codegen.run
```

## How to verify

After running the command, verify the files exist:

```bash
ls apps/api-gateway/openapi/openapi_summary.json apps/api-gateway/openapi/openapi_paths.txt
```

Expected output:

```text
apps/api-gateway/openapi/openapi_summary.json
apps/api-gateway/openapi/openapi_paths.txt
```

## Key files

- `tools/codegen/run.py`: validation + summary generator.
- `tools/codegen/codegen_config.yaml`: spec path and output settings.
- `docs/api/openapi.yaml`: source specification.

## Example

Print the first five API paths after generation:

```bash
python -m tools.codegen.run
head -n 5 apps/api-gateway/openapi/openapi_paths.txt
```

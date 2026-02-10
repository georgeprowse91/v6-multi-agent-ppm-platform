# Ops config schemas

`ops/tools/config_validator.py` validates configuration files in `ops/config/` by matching each
config file name to a schema in this folder:

- `ops/config/**/intent-routing.yaml` → `ops/schemas/intent-routing.schema.json`
- `ops/config/**/approval_policies.yaml` or `.json` → `ops/schemas/approval_policies.schema.json`
- `ops/config/**/business-case-settings.yaml` → `ops/schemas/business-case-settings.schema.json`
- `ops/config/**/intent-router.yaml` → `ops/schemas/intent-router.schema.json`

## Extending validation for new config files

1. Add a JSON schema with the filename pattern `<config-stem>.schema.json`.
2. Place the schema in `ops/schemas/`.
3. Ensure the target config file in `ops/config/` uses the same stem.
4. Run `python ops/tools/config_validator.py` locally before committing.

The validator skips files without a matching schema and reports them in output so teams can
incrementally increase schema coverage.

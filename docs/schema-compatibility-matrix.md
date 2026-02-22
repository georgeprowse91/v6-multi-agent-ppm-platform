# Schema Compatibility Matrix and Tooling

This project ships a schema registry and compatibility checker for JSON schemas in:

- `data/schemas/*.schema.json`
- `ops/schemas/*.schema.json`
- Additional schema roots configured in `ops/scripts/schema_registry.py`.

## Schema metadata contract

Each schema can declare:

```json
"x-schema-metadata": {
  "name": "project",
  "version": "1.0.0",
  "compatibility_mode": "full"
}
```

- `name`: stable logical schema name.
- `version`: semantic version (`MAJOR.MINOR.PATCH`).
- `compatibility_mode`:
  - `backward`
  - `forward`
  - `full`

## Compatibility matrix

| Detected change type | Example | Backward | Forward | Full |
|---|---|---|---|---|
| `patch` | Non-structural/no-op changes | ✅ | ✅ | ✅ |
| `minor` | Add optional field / enum expansion | ✅ | ❌ | ❌ |
| `major` | Remove/retarget fields, add required fields, type narrowing | ❌ | ❌ | ❌ |

## CLI commands

Validate schema registry metadata and JSON Schema syntax:

```bash
python ops/scripts/schema_tool.py validate
```

Run compatibility check for a single schema against a base ref:

```bash
python ops/scripts/schema_tool.py compatibility data/schemas/project.schema.json --base-ref origin/main --mode full
```

Enforce semantic version bumps based on detected change type:

```bash
python ops/scripts/schema_tool.py enforce-bumps
```

Create migration scaffold for a breaking change:

```bash
python ops/scripts/schema_tool.py migration scaffold --schema project --from-version 1.0.0 --to-version 2.0.0
```

Dry-run migration against fixture snapshots in `data/schemas/examples/`:

```bash
python ops/scripts/schema_tool.py migration dry-run --schema project --from-version 1.0.0 --to-version 2.0.0
```

## CI wiring

CI runs:

1. `python ops/scripts/validate-schemas.py`
2. `python ops/scripts/schema_tool.py enforce-bumps`

This ensures schema pull requests fail when:

- schema metadata is invalid,
- compatibility mode is violated,
- semantic version bump is insufficient for the detected change type.

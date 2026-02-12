# Placeholder Token Standard

This standard defines how canonical templates declare and render placeholder tokens.

## 1) Token syntax

Use double-curly token syntax:

- `{{project_name}}`
- `{{total_budget}}`

Rules:

1. Tokens are lowercase `snake_case` names inside `{{` and `}}`.
2. Token names MUST match the `placeholders[].key`/registry key after normalization.
3. Tokens may appear in `sections[].consumes_placeholders` and `placeholders[].token`.

## 2) Escaping conventions

When a literal `{{` or `}}` is needed in output text, escape braces by prefixing each brace with `\`:

- Literal open braces: `\{\{`
- Literal close braces: `\}\}`

Renderers should unescape `\{\{` → `{{` and `\}\}` → `}}` after token replacement.

## 3) Default value conventions

Defaults are controlled by mapping metadata (see `mappings/template-field-map.json`):

- **required + no fallback**: fail binding and report missing token.
- **required + fallback**: bind fallback value and log warning.
- **optional + fallback**: bind fallback if source data is null/empty.
- **optional + no fallback**: replace with empty string.

## 4) Validation conventions

Validation should run before substitution:

- Enforce declared data type.
- Apply validation hints (regex, min/max, currency constraints, etc.).
- Reject invalid required tokens before rendering.

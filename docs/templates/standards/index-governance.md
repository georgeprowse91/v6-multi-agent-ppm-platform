# Template Index Governance

## Purpose
This policy defines how to maintain `docs/templates/index.json` so canonical template entries stay complete, accurate, and auditable.

## Scope
Applies to:
- Base templates under `docs/templates/core/*/base.yaml`
- Methodology extension patches under `docs/templates/extensions/*/*.patch.yaml`
- The canonical index at `docs/templates/index.json`

## Index schema requirements
Each canonical entry must include:
- `template_id`
- `path`
- `artefact_type`
- `methodology`
- `compliance_tags`
- `version`
- `status`
- `replaces`
- `supports_modular`

Optional:
- `required_fields`
- `placeholder_schema_ref`

## Add a new canonical template

1. Create the base or extension file in `core/` or `extensions/`.
2. Add one new object in `index.json` with all required fields.
3. Ensure:
   - `path` matches the file location exactly.
   - `template_id` is unique and follows naming rules.
   - `status` is valid (`draft`, `active`, `deprecated`, `retired`).
   - `supports_modular=true` only for templates designed to be extended.
4. If adding an extension:
   - Set `replaces` to the related universal/base template ID.
   - Set `placeholder_schema_ref` to the base schema path.
5. Update `docs/templates/README.md` category sections and methodology lists.

## Update an existing canonical template

Use **minor** version bumps for additive/non-breaking changes and **major** bumps for structural breaks.

1. Update the template file.
2. Update matching `index.json` fields:
   - `version`
   - `required_fields` (if changed)
   - `placeholder_schema_ref` (if base linkage changed)
3. If `template_id` changes because of major versioning, add a new entry and deprecate the old one.
4. Refresh README links if files moved or IDs changed.

## Deprecate or retire a template

1. Keep the entry in `index.json` and change:
   - `status: deprecated` (or `retired`)
   - `replaced_by` pointing to the successor template ID
   - Keep `replaces` unchanged so historical lineage is not lost.
2. For deprecated entries, include lifecycle metadata:
   - `deprecation_version`
   - `sunset_date` (required for `deprecated`, optional for `retired`)
   - `aliases` when a legacy file name or prior ID must still resolve.
3. Do not delete historical entries used by existing automation.
4. Add/refresh migration guidance in:
   - `docs/templates/README.md`
   - `docs/templates/standards/template-naming-rules.md` (legacy mapping table)

## Quality checks before merge

- JSON is valid and formatted.
- Every `path` in index exists.
- Every entry has required fields.
- No duplicate `template_id` values.
- README links resolve for all base/extension references.

## Ownership and review

- **Primary owner:** Template maintainers (PMO / methodology owners).
- **Review expectation:** Any PR that changes `core/` or `extensions/` must include corresponding `index.json` and README updates.

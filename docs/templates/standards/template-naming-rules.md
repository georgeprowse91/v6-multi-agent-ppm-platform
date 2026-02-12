# Template Naming Rules Standard

## Purpose
This document defines canonical naming and metadata rules for templates in `docs/templates/`, including compatibility handling for legacy names.

## 1) Required Metadata Fields
Every template must include (front matter, YAML header, or equivalent structured block) the following fields:

- `template_id`  
  Canonical ID matching the filename stem exactly.
- `artefact_type`  
  Primary artefact class from taxonomy (e.g., `charter`, `risk-register`, `roadmap`).
- `methodology`  
  Method delivery model (e.g., `agile`, `waterfall`, `hybrid`, `safe`, `traditional`).
- `version`  
  Semantic template version (e.g., `1`, `1.1`, `2`).
- `status`  
  Lifecycle state; allowed: `draft`, `active`, `deprecated`, `retired`.

### Recommended extended fields
- `governance_tier`
- `regulation_scope`
- `industry`
- `aliases` (list of old names)
- `replaces` (prior canonical ID)
- `owner`
- `last_reviewed`

## 2) Canonical Naming Format

### Canonical ID
```text
<artefact>[.<methodology>][.<governance_tier>][.<regulation_scope>][.<industry>].v<major>[.<minor>]
```

### Canonical filename
```text
<artefact>[.<methodology>][.<governance_tier>][.<regulation_scope>][.<industry>].v<major>[.<minor>].<ext>
```

Where:
- `<ext>` is usually `yaml` (preferred for structured templates) or `md` (narrative templates).
- All segments are lowercase kebab-case.
- Segment ordering is fixed and must not be rearranged.

## 3) Backward Compatibility and Deprecation Rules

### 3.1 Legacy name support
When renaming an existing template:
1. Keep the legacy filename for at least one minor cycle OR add an alias registry entry.
2. Add legacy names to `aliases` metadata in the canonical template.
3. Include a migration pointer in the legacy file header/body:
   - `Deprecated: use <canonical_filename>`.
4. Preserve links by updating known references in docs where feasible.

### 3.2 Deprecation lifecycle
- `active` → default usable template.
- `deprecated` → still available, migration required, must declare replacement.
- `retired` → no longer valid for new use; may remain for audit history.

Required deprecation metadata:
- `status: deprecated`
- `replaced_by: <canonical template_id>`
- `deprecation_version: <version>`
- `sunset_date: YYYY-MM-DD` (recommended)

### 3.3 Compatibility guarantees
- Canonical IDs are immutable once published.
- Version increments:
  - Major (`v1` → `v2`) for incompatible structural changes.
  - Minor (`v1.0` → `v1.1`) for additive backward-compatible updates.
- Legacy aliases must resolve deterministically to one canonical ID.

## 4) Examples: Legacy → Canonical Mappings
Examples below map currently observed filenames under `docs/templates/**` to canonical names.

| Legacy filename | Canonical filename |
|---|---|
| `docs/templates/business_case_template.md` | `docs/templates/business-case.traditional.project.cross-industry.v1.md` |
| `docs/templates/project_charter_template.md` | `docs/templates/charter.traditional.project.cross-industry.v1.md` |
| `docs/templates/program_charter_template.md` | `docs/templates/charter.traditional.program.cross-industry.v1.md` |
| `docs/templates/risk_register_template.md` | `docs/templates/risk-register.traditional.project.cross-industry.v1.md` |
| `docs/templates/it-risk-register.md` | `docs/templates/risk-register.traditional.project.none.software.v1.md` |
| `docs/templates/healthcare-risk-register.md` | `docs/templates/risk-register.traditional.project.hipaa.healthcare.v1.md` |
| `docs/templates/technology-adoption-roadmap.md` | `docs/templates/roadmap.hybrid.program.cross-industry.v1.md` |
| `docs/templates/security-implementation-roadmap.md` | `docs/templates/roadmap.hybrid.program.iso27001.software.v1.md` |
| `docs/templates/governance-assessment-template.md` | `docs/templates/compliance-assessment.traditional.enterprise.cross-industry.v1.md` |
| `docs/templates/gxp-compliance-checklist.md` | `docs/templates/compliance-assessment.traditional.project.gxp.pharmaceutical.v1.md` |

> Note: These mappings are examples for normalization policy and can be adjusted when domain owners provide stricter classification metadata.

## 5) Lightweight Maintainer Lint Checklist

- [ ] Template contains required metadata: `template_id`, `artefact_type`, `methodology`, `version`, `status`.
- [ ] `template_id` equals filename stem exactly.
- [ ] `artefact_type` is valid per taxonomy standard.
- [ ] Filename uses lowercase kebab-case segments and canonical ordering.
- [ ] `status` is one of: `draft`, `active`, `deprecated`, `retired`.
- [ ] Deprecated templates include `replaced_by` and deprecation version/date fields.
- [ ] Any renamed legacy file is recorded in `aliases` or an alias mapping table.
- [ ] Version bumps follow compatibility policy (major for breaking, minor for additive).

### Script-ready lint hints
- Required key presence check (YAML/Front Matter parse).
- Regex filename validation.
- `template_id` to filename-stem equality check.
- vocabulary validation for `artefact_type`, `methodology`, and `status`.
- alias uniqueness check (no one legacy name maps to multiple canonical IDs).

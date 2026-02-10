# Data Model Propagation & Scenario Guidance

## Purpose

Define canonical propagation rules, conflict handling, and scenario guidance beyond the entity list already documented.

## Canonical Entities & Ownership

Canonical entities and primary owners are maintained in the canonical data model documentation. See [Canonical Data Model](../data/data-model.md).

## Propagation Rules (WBS → Schedule → Risk/Budget)

- **Canonical ownership first:** The owning agent/service is the source of truth for its entity; downstream systems consume canonical records rather than rewriting them.
- **Directional propagation:** Work breakdown structure (WBS) changes flow into schedule work items, which then inform downstream risk and budget entities.
- **Mode-aware application:**
  - **merge:** update only fields present in the incoming payload, preserving existing canonical values.
  - **replace:** overwrite the canonical payload with the incoming payload.
  - **enrich:** append non-null fields without overwriting existing canonical values.
- **Field-level constraints:** Only mapped target fields propagate; unmapped fields are ignored to prevent schema drift.
- **Lineage requirements:** Each propagation emits lineage metadata with source system, entity, transformation, and timestamp.

## Conflict Handling & Audit Expectations

- **Conflict policy:**
  - **source_of_truth:** accept updates from the declared owner system.
  - **last_write_wins:** prefer the most recent `updated_at` timestamp.
  - **manual_required:** record conflicts when ownership is ambiguous or an approval gate is configured.
- **Audit trail:** Conflicts and resolution strategies must be logged with source, target, timestamps, and applied policy.
- **Review workflow:** Manual conflicts remain in a review queue until resolved and re-propagated.

## Scenario Modeling (Baseline vs Variants)

- **Baseline scenario:** The baseline captures the approved plan for schedule, risk, and budget. Canonical entities represent the baseline unless a scenario tag indicates otherwise.
- **Variant scenarios:** Variants inherit from the baseline and override only the changed entities. Variants must retain a pointer to the baseline identifier for traceability.
- **Propagation scope:**
  - Baseline updates cascade to variants only when explicitly rebaselined.
  - Variant updates never overwrite baseline records; they propagate only within the same scenario context.

## Canonical Storage Context

Canonical entities and schema versions are stored and served by the Data Service. See [Data Service README](../../services/data-service/README.md).

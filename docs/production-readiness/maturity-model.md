# Engineering Maturity Model

## Purpose

Define an objective and enforceable maturity model that converts delivery, operational, and governance signals into a release decision.

## Dimensions and KPI definitions

The model is encoded in [`ops/ops/config/maturity_model.yaml`](../../ops/ops/config/maturity_model.yaml) and scored by [`ops/tools/collect_maturity_score.py`](../../ops/tools/collect_maturity_score.py).

| Dimension | Example KPIs (measurable) | Target intent |
| --- | --- | --- |
| Reliability | `slo_pass_rate`, `mttr_minutes` | SLO adherence + faster incident recovery |
| Scalability | `p95_latency_ms`, `headroom_percent` | Capacity and latency resilience under load |
| Security | `critical_vulnerability_count`, `secret_findings` | Zero critical findings at release time |
| Operability | `alert_actionability_percent`, `config_drift_violations` | Reduce alert noise and drift |
| Test Coverage | `backend_coverage_percent`, `frontend_coverage_percent` | Coverage baseline with incremental uplift |
| Documentation | `stale_doc_count`, `runbook_sla_percent` | Fresh docs and runbooks tied to changes |
| DR/Backup | `backup_success_percent`, `restore_rto_minutes` | Proven backup reliability + restore readiness |
| Dependency Hygiene | `dependency_age_p95_days`, `unpinned_dependency_count` | Healthy patch currency and deterministic builds |

Each KPI defines:

- artifact source (`artifacts/.../*.json`)
- JSON path selector
- scoring direction (`higher_is_better` / `lower_is_better`)
- floor and target bounds for 0..100 score normalization

## Release eligibility thresholds

Release is eligible only if all conditions pass:

1. Overall weighted score >= `minimum_overall_score`.
2. Every dimension score >= `minimum_dimension_score`.
3. Mandatory dimensions (`Reliability`, `Security`, `Test Coverage`) also meet the dimension threshold.

Current baseline policy is stored in `release_policy` and enforced by:

```bash
python ops/tools/collect_maturity_score.py --enforce-thresholds
```

## Ratcheting policy

Thresholds increase quarterly through the `ratchet_policy.schedule` table in `ops/ops/config/maturity_model.yaml`.

- The collector resolves the active threshold set by `effective_date`.
- Teams should only move thresholds upward (no downward edits) unless an incident postmortem approves an exception.
- Ratchet updates should land before the first release planning cycle of each quarter.

## Publishing snapshots and backlog generation

The collector writes:

- JSON scorecard: `artifacts/maturity/scorecard-latest.json`
- Markdown snapshot: `docs/production-readiness/maturity-scorecards/latest.md`

The scorecard includes a **monthly backlog** generated from the three lowest-scoring dimensions. Product/engineering planning should create explicit backlog items from this section each month.

## CI usage

Suggested CI step:

```bash
python ops/tools/collect_maturity_score.py --artifact-root . --enforce-thresholds
```

Publish the JSON and markdown outputs as workflow artifacts so the release decision is auditable and trendable over time.

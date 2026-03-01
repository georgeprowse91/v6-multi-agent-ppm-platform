# Human-in-the-loop checkpoints beyond approvals

This platform extends human oversight to critical autonomous decisions, not only formal approval workflows.

## Critical actions under review

The orchestrator now evaluates agent-proposed actions against `ops/ops/config/human_review.yaml` rules. Current high-impact checkpoints include:

- **Risk mitigation recommendations** from the Risk Management agent when `risk_score` is above threshold.
- **Schedule adjustments** from the Schedule Planning agent when timeline impact is material.
- **Resource reallocations** from the Resource Management agent when a significant percentage shift is proposed.

## Review configuration

Rules are configured in `ops/ops/config/human_review.yaml` under `review_rules`:

- `action_type`: canonical action category emitted by an agent.
- `agent_ids`: agent identifiers subject to the rule.
- `conditions`: field/operator/value checks against action and result payload content.
- `decision_timeout_seconds`: max wait for a reviewer decision before defaulting to reject.

## Runtime flow

1. Agent task completes and returns proposed actions.
2. Orchestrator checks actions against configured human-review rules.
3. If matched, orchestrator pauses that action and emits `human_review_required` with:
   - correlation ID
   - task and agent IDs
   - proposed action details
   - relevant context/dependency/result data
4. Orchestrator awaits `human_review_decision` (`approve`, `reject`, `modify`).
5. Orchestrator applies decision:
   - `approve`: action proceeds with `approved_by_human_review` status.
   - `reject`: action marked `rejected_by_human_review` and should be skipped by downstream handlers.
   - `modify`: action payload overwritten with reviewer-provided `modified_action` and marked `modified_by_human_review`.

## Review queue for tests

The orchestrator maintains an in-memory queue of pending reviews and exposes it via `get_pending_human_reviews()` to support deterministic tests and local tooling.

## Event contract summary

- **Outbound:** `human_review_required`
- **Inbound:** `human_review_decision`

Both events include `review_id` for correlation; orchestrator also propagates workflow-level `correlation_id`.

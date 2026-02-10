# Agent Feedback Mechanism

This repository includes a built-in feedback capture path so clients can collect explicit user quality signals for agent responses and store them for offline analysis/model improvement.

## What was added

- A typed feedback model in `packages/feedback/feedback_models.py`.
- A persistence service in `services/feedback_service.py` backed by SQLite.
- `BaseAgent.send_feedback(...)` for associating feedback to a specific run via `correlation_id`.
- A `request_feedback` boolean added to the standard `AgentResponse` contract.

## Feedback schema

`Feedback` is a dataclass with:

- `correlation_id`: run-level correlation identifier (required).
- `agent_id`: agent identifier the feedback applies to (required).
- `user_rating`: integer score from 1 to 5.
- `comments`: free-form user commentary.
- `corrected_response`: optional user-provided correction.

Validation rules:

- `user_rating` must be in range `1..5`.
- `correlation_id` and `agent_id` must be non-empty.

## Enabling feedback prompts in agent responses

`AgentResponse` now includes `request_feedback`.

- Default: `False`.
- To enable for a specific agent instance, set config:

```python
agent = SomeAgent(
    agent_id="my-agent",
    config={
        "request_feedback": True,
    },
)
```

When true, clients should render a feedback form after showing the response.

## Persisting feedback

`BaseAgent` constructs a `FeedbackService` and exposes:

```python
agent.send_feedback(feedback)
```

Where `feedback` can be either:

- a `Feedback` instance, or
- a `dict` that can be parsed into `Feedback`.

If `feedback.agent_id` does not match the current agent instance, the call raises `ValueError`.

### Storage backend

- Default SQLite file: `data/feedback.sqlite3`.
- Override via agent config key `feedback_db_path` or env var `FEEDBACK_DB_PATH`.

Schema (`feedback` table):

- `correlation_id`
- `agent_id`
- `user_rating`
- `comments`
- `corrected_response`
- `created_at`

## How feedback is used

Collected feedback can be used to:

- identify low-rated responses by intent/agent,
- analyze recurring failure patterns from comments,
- build supervised datasets from `corrected_response`,
- prioritize prompt/tooling/model improvements per agent.

A typical flow:

1. Agent executes and returns `correlation_id` + `request_feedback`.
2. UI/API gathers rating and optional correction from user.
3. API layer calls `agent.send_feedback(...)`.
4. Offline analytics jobs query feedback records for quality dashboards and training inputs.

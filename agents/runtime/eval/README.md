# Agent Runtime Evaluation

## Purpose

Track evaluation assets and outputs for the runtime agent stack.

## What's inside

- `README.md`: Documentation for this directory.
- `manifest.yaml`: Evaluation manifest with stage checks, expected output assertions, and multi-agent flow definitions.
- [](/fixtures/): Stage-scoped fixture sets for regression checks.
- `run_eval.py`: Lightweight harness that validates the manifest and fixtures.

## How it's used

Evaluation assets are consumed by the runtime evaluation tooling under `agents/runtime/`.
The fixtures are grouped by orchestration stage (definition, prompt, tools) to keep
regression checks aligned with the runtime pipeline.

## How to run / develop / test

```bash
python agents/runtime/eval/run_eval.py --manifest agents/runtime/eval/manifest.yaml
```

## Configuration

No direct configuration; evaluation tooling reads files from this directory.

## Troubleshooting

- Missing evaluation inputs: add the required fixtures or manifests to this folder.
- Evaluation failures: verify schema compatibility with the runtime evaluator.


## Manifest features

- `assertions`: Validate fixture fields directly (legacy behavior).
- `expected_outputs`: Validate agent output fields from `actual_output`, `output`, or `response` in each fixture.
- `multi_agent_flows`: Define flow steps and validate each step's fixture outputs for cross-agent scenarios.

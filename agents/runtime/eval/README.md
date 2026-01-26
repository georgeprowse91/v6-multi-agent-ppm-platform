# Agent Runtime Evaluation

## Purpose

Track evaluation assets and outputs for the runtime agent stack.

## What's inside

- `README.md`: Documentation for this directory.

## How it's used

Evaluation assets are consumed by the runtime evaluation tooling under `agents/runtime/`.

## How to run / develop / test

```bash
ls agents/runtime/eval
```

## Configuration

No direct configuration; evaluation tooling reads files from this directory.

## Troubleshooting

- Missing evaluation inputs: add the required fixtures or manifests to this folder.
- Evaluation failures: verify schema compatibility with the runtime evaluator.
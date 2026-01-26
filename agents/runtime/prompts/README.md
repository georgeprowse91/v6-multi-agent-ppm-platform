# Agent Runtime Prompts

## Purpose

Store prompt templates used by the agent runtime during orchestration and tool execution.

## What's inside

- `agents/runtime/prompts/examples`: Example configurations and demo scenarios.
- `agents/runtime/prompts/schema`: Schemas or validation rules for component assets.
- `agents/runtime/prompts/prompt_registry.py`: Python module used by this component.

## How it's used

Prompts are loaded by runtime components under `agents/runtime/` and referenced in agent specs.

## How to run / develop / test

```bash
ls agents/runtime/prompts
```

## Configuration

No additional configuration; prompt selection is handled in runtime code.

## Troubleshooting

- Missing prompt errors: ensure referenced prompt files exist in this folder.
- Formatting issues: validate prompt templates are valid YAML or Markdown, depending on usage.
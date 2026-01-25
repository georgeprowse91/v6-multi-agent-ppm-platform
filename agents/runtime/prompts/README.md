# Runtime Prompt Definitions

## Purpose
Prompt definitions describe the system and user prompt scaffolding used by runtime agents. They
provide an auditable source of truth for prompt versions used by the orchestration service. Prompt
files are enumerated by `agents/runtime/prompts/prompt_registry.py`.

## Responsibilities
- Store versioned prompt YAML used by agents.
- Capture ownership and descriptions for each prompt.
- Validate prompt files against the prompt schema.

## Folder structure
```
agents/runtime/prompts/
├── README.md
├── examples/
│   └── intent-router.prompt.yaml
└── schema/
    └── prompt.schema.json
```

## Conventions
- Use `apiVersion: ppm.prompts/v1` and `kind: Prompt`.
- Prompt files end in `.prompt.yaml`.
- Increment `metadata.version` when prompt text changes.

## How to add a new prompt
1. Copy `examples/intent-router.prompt.yaml` and update `metadata` and prompt text.
2. Keep tool names in `prompt.tools` aligned with registered agent tools.
3. Validate with the script below.
4. Confirm the new file is listed by `agents/runtime/prompts/prompt_registry.py`.

## How to validate/test
```bash
python scripts/validate-prompts.py agents/runtime/prompts/examples/intent-router.prompt.yaml
```

## Example
```yaml
apiVersion: ppm.prompts/v1
kind: Prompt
metadata:
  name: intent-router-v1
  owner: core-orchestration
  version: "1.0.0"
prompt:
  system: |
    You are the intent router for the Multi-Agent PPM Platform.
  user: |
    Classify the request: {{ request.text }}
```

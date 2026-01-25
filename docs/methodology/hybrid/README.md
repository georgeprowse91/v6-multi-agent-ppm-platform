# Hybrid Methodology

## Purpose

Describe the hybrid methodology that blends Waterfall gates with Agile execution cycles.

## Architecture-level context

Hybrid maps combine phase-based governance with iterative delivery. Gate checks ensure formal approvals while iterative cycles deliver incremental value. This is common for regulated programs requiring formal sign-offs.

## What the YAML means

- `map.yaml`: phase gates with embedded iteration loops.
- `gates.yaml`: approvals for phase transitions and iteration readiness.

## Example workflow

1. **Initiation gate**: approve charter and funding.
2. **Iterative delivery**: execute increments within Planning/Execution phases.
3. **Phase gate**: review outcomes and approve next phase.
4. **Closing**: post-implementation review and benefits tracking.

## Usage example

Inspect the hybrid map:

```bash
sed -n '1,120p' docs/methodology/hybrid/map.yaml
```

## How to verify

List hybrid templates:

```bash
ls docs/methodology/hybrid/templates
```

Expected output includes `governance-pack.md` and `hybrid-charter.md`.

## Implementation status

- **Implemented**: Hybrid map and templates.
- **Planned**: automated gate logic via workflow engine.

## Related docs

- [Methodology Overview](../overview.md)
- [Approval Workflow Agent](../../architecture/agent-orchestration.md)

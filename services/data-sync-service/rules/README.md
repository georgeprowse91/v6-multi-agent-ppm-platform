# Sync Rules

This folder contains YAML rule definitions consumed by the data sync service. The runtime loads all
`*.yaml` files and plans reconciliation jobs based on their IDs.

## Example

```yaml
id: ds-001
description: Default merge of connector work items into canonical model
source: connector-hub
target: canonical-work-items
mode: merge
filters:
  status: active
```

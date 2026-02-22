# Policy Engine endpoint reference

Source: `services/policy-engine/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `POST` | `/v1/abac/evaluate` | `evaluate_abac` |
| `POST` | `/v1/compliance/evaluate` | `evaluate_compliance` |
| `POST` | `/v1/ops/config/evaluate` | `evaluate_policies` |
| `POST` | `/v1/rbac/evaluate` | `evaluate_rbac` |
| `GET` | `/version` | `version` |

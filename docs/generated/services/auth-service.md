# Auth Service endpoint reference

Source: `services/auth-service/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `POST` | `/v1/auth/login` | `login` |
| `POST` | `/v1/auth/logout` | `logout` |
| `GET` | `/v1/auth/me` | `whoami` |
| `POST` | `/v1/auth/refresh` | `refresh` |
| `POST` | `/v1/auth/validate` | `validate_auth` |
| `GET` | `/version` | `version` |

# API Gateway - API Module

Core API module containing route definitions, middleware, and request/response schemas for the API gateway.

## Directory structure

| Folder | Description |
| --- | --- |
| [routes/](./routes/) | API route handlers |
| [middleware/](./middleware/) | Request middleware |
| [schemas/](./schemas/) | Request/response schemas |

## Key files

| File | Description |
| --- | --- |
| `main.py` | API module entrypoint |
| `config.py` | API-level configuration |
| `limiter.py` | Rate limiting logic |
| `circuit_breaker.py` | Circuit breaker for downstream resilience |

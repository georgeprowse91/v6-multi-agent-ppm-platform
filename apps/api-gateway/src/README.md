# API Gateway Source

Source code for the API gateway application, which serves as the front door for all client requests.

## Directory structure

| Folder | Description |
| --- | --- |
| [api/](./api/) | API route handlers, middleware, and request/response schemas |

## Key files

| File | Description |
| --- | --- |
| `main.py` | Application entrypoint |
| `config.py` | Gateway configuration |
| `limiter.py` | Rate limiting logic |
| `circuit_breaker.py` | Circuit breaker for downstream resilience |
| `connector_loader.py` | Dynamic connector loading |
| `runtime_bootstrap.py` | Runtime initialization and bootstrap |

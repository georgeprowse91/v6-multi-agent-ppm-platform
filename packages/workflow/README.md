# Workflow

Workflow dispatchers, Celery tasks, and result aggregation for orchestrating platform operations.

## Directory structure

| Folder | Description |
|--------|-------------|
| [src/workflow/](./src/workflow/) | Core workflow module |

## Key files

| File | Description |
|------|-------------|
| `src/workflow/dispatcher.py` | Workflow dispatch logic |
| `src/workflow/celery_app.py` | Celery application configuration |
| `src/workflow/executor.py` | Workflow execution engine |
| `src/workflow/tasks.py` | Celery task definitions |
| `src/workflow/aggregation.py` | Result aggregation utilities |

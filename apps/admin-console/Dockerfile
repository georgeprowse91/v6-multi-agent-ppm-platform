# syntax=docker/dockerfile:1.6
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY --from=repo-root pyproject.toml ./
COPY --from=repo-root tools ./tools
COPY --from=repo-root config ./config
COPY --from=repo-root packages ./packages
COPY --from=repo-root agents ./agents
COPY . /app/apps/admin-console


RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "tools.component_runner", "--component-type", "app", "--component-name", "admin-console", "--component-root", "/app/apps/admin-console"]

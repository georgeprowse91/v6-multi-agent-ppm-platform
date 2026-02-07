#!/usr/bin/env bash
set -euo pipefail

python scripts/validate-schemas.py
python scripts/validate-manifests.py
python scripts/validate-helm-charts.py
python scripts/check-links.py

ruff check agents/ apps/ packages/ tests/ --output-format=github
black --check agents/ apps/ packages/ tests/

pytest tests/ -v --cov=agents --cov=apps --cov=packages --cov=tools --cov-report=term-missing --cov-fail-under=80
pytest tests/integration -v
pytest tests/e2e -v
pytest tests/load -v

if [[ -n "${LOAD_TEST_TARGET:-}" ]]; then
  python scripts/load-test.py --profile tests/load/sla_targets.json --target "$LOAD_TEST_TARGET"
fi

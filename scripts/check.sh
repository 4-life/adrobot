#!/usr/bin/env bash
# Static checks and unit tests. Reports problems; never fixes them.
set -euo pipefail
cd "$(dirname "$0")/.."

SCHEMA=backend/app/tracker/keitaro/openapi.yaml
MODELS=backend/app/tracker/keitaro/models.py

echo "== backend: Keitaro models =="
# The schema is git-ignored (not ours to publish); models.py is committed. With the schema
# present locally, the models are regenerated from it (commit any change); without it, as in
# CI, the committed models.py is used.
if [[ -f "$SCHEMA" ]]; then
  bash scripts/gen-keitaro.sh
elif [[ ! -f "$MODELS" ]]; then
  echo "$MODELS is missing: download the Keitaro schema to $SCHEMA, then run scripts/gen-keitaro.sh"
  exit 1
fi

echo "== backend: ruff =="
(cd backend && uv run ruff check . && uv run ruff format --check .)

echo "== backend: mypy =="
(cd backend && uv run mypy app tests)

echo "== backend: pytest =="
(cd backend && uv run pytest)

echo "== dashboard: typecheck =="
(cd dashboard && npm run typecheck)

echo "All checks passed."

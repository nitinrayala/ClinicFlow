#!/bin/sh
set -eu
CLINICFLOW_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$CLINICFLOW_ROOT"
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
# The backend reads ../.env; do not execute .env as shell code.
cd backend
../.venv/bin/python -m alembic upgrade head
../.venv/bin/python -m app.seed
cd ../frontend
npm ci
printf '%s\n' 'Setup complete. Run sh scripts/dev.sh from the repository root.'


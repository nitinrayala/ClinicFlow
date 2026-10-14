#!/bin/sh
set -eu
CLINICFLOW_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$CLINICFLOW_ROOT"
mkdir -p .local
CLINICFLOW_API_PID=''
CLINICFLOW_UI_PID=''
cleanup() {
    if [ -n "$CLINICFLOW_API_PID" ]; then kill "$CLINICFLOW_API_PID" 2>/dev/null || true; fi
    if [ -n "$CLINICFLOW_UI_PID" ]; then kill "$CLINICFLOW_UI_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM
(
    cd "$CLINICFLOW_ROOT/backend"
    exec ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
) >.local/api.log 2>&1 &
CLINICFLOW_API_PID=$!
(
    cd "$CLINICFLOW_ROOT/frontend"
    exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
) >.local/ui.log 2>&1 &
CLINICFLOW_UI_PID=$!
printf '%s\n' 'App: http://127.0.0.1:5173. Ctrl+C stops both servers. Logs are in .local/.'
wait "$CLINICFLOW_API_PID" "$CLINICFLOW_UI_PID"


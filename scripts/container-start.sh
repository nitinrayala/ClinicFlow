#!/bin/sh
set -eu
# Schema changes and seeding are separate release operations, never per worker.
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'


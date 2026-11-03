#!/usr/bin/env bash
# Cada réplica solo arranca: catalog-init ya migró y sembró (ver scripts/init.sh).
set -euo pipefail

exec uvicorn app.main:app --host 0.0.0.0 --port 8000

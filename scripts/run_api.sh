#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cd services/api
export PYTHONPATH="$PWD"
export NEUROFORGE_SCHEDULER="${NEUROFORGE_SCHEDULER:-1}"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8077 --reload

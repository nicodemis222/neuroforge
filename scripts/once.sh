#!/usr/bin/env bash
# Run a single intervention loop synchronously — useful for first-run.
# Usage: ./scripts/once.sh lions_mane
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
VENV="$ROOT/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "[once] no venv found — run ./scripts/run_api.sh once to create it." >&2
  exit 1
fi
cd "$ROOT/services/api"
export PYTHONPATH="$PWD"
KEY="${1:-clemastine}"
"$VENV/bin/python" -c "
import asyncio
from app.scheduler import run_one_intervention
from app.ontology import INTERVENTIONS_BY_KEY
iv = INTERVENTIONS_BY_KEY['$KEY']
asyncio.run(run_one_intervention(iv))
"

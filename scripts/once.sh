#!/usr/bin/env bash
# Run a single intervention loop synchronously — useful for first-run.
# Usage: ./scripts/once.sh lions_mane
set -euo pipefail
cd "$(dirname "$0")/../services/api"
export PYTHONPATH="$PWD"
KEY="${1:-clemastine}"
python -c "
import asyncio
from app.scheduler import run_one_intervention
from app.ontology import INTERVENTIONS_BY_KEY
iv = INTERVENTIONS_BY_KEY['$KEY']
asyncio.run(run_one_intervention(iv))
"

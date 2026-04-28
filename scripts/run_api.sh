#!/usr/bin/env bash
# Start the NEUROFORGE API + scheduler.
# Auto-bootstraps a venv at <repo>/.venv on first run so this works on
# Homebrew Python (PEP 668) and any other distro without polluting site-packages.
set -euo pipefail
cd "$(dirname "$0")/.."

ROOT="$PWD"
VENV="$ROOT/.venv"

if [ ! -x "$VENV/bin/python" ]; then
  echo "[run_api] creating venv at $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
fi

# Install/refresh deps if pyproject changed since last install.
NEED_INSTALL=1
if [ -f "$VENV/.last_install" ]; then
  if [ "$ROOT/services/api/pyproject.toml" -ot "$VENV/.last_install" ]; then
    NEED_INSTALL=0
  fi
fi
if [ "$NEED_INSTALL" = "1" ]; then
  echo "[run_api] installing API deps"
  "$VENV/bin/pip" install --quiet -e "$ROOT/services/api"
  touch "$VENV/.last_install"
fi

cd "$ROOT/services/api"
export PYTHONPATH="$PWD"
export NEUROFORGE_SCHEDULER="${NEUROFORGE_SCHEDULER:-1}"
exec "$VENV/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8077 --reload

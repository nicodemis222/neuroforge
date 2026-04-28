#!/usr/bin/env bash
# Re-extract patient profile from data/patient_corpus/*.pdf.
# Requires Ollama running locally with qwen3.5:7b (best) or any chat model.
set -euo pipefail
cd "$(dirname "$0")/../services/api"
export PYTHONPATH="$PWD"
python -m app.seed.extractor

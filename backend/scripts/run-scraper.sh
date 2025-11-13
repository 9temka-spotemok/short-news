#!/bin/sh
set -eu

cd /app

PYTHON_BIN="$(command -v python3 || command -v python)"
exec "$PYTHON_BIN" scripts/scrape_all_companies.py "$@"


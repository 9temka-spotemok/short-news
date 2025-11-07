#!/bin/sh
set -eu

cd /app

python scripts/scrape_all_companies.py "$@"


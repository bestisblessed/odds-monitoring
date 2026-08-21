#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/home/durrrrr/.pyenv/shims/python"
LOG_FILE="${SCRIPT_DIR}/Scraping/log.log"

mkdir -p "${SCRIPT_DIR}/Scraping/data/odds"
date
echo "Scraping NFL VSIN odds..."
"${PYTHON}" "${SCRIPT_DIR}/Scraping/nfl.py" >> "${LOG_FILE}" 2>&1
echo "HEALTHCHECK_OK: nfl-odds-scraper"

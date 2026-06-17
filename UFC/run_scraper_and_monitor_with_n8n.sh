#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRAPE_MONEYLINES=true
SCRAPE_TOTALS=false

export SCRAPE_MONEYLINES
export SCRAPE_TOTALS

date

SCRAPE_MONEYLINES="${SCRAPE_MONEYLINES,,}"
SCRAPE_TOTALS="${SCRAPE_TOTALS,,}"

if [ "$SCRAPE_MONEYLINES" = true ]; then
    echo "Scraping moneylines..."
    /home/durrrrr/.pyenv/shims/python "${SCRIPT_DIR}/Scraping/ufc_v2.py" >> "${SCRIPT_DIR}/Scraping/log.log" 2>&1
else
    echo "Moneylines scraping disabled"
fi

sleep 1

if [ "$SCRAPE_TOTALS" = true ]; then
    echo "Scraping totals..."
    /home/durrrrr/.pyenv/shims/python "${SCRIPT_DIR}/Scraping/ufc_totals.py" >> "${SCRIPT_DIR}/Scraping/log_totals.log" 2>&1
else
    echo "Totals scraping disabled"
fi

sleep 1

echo "Running monitoring with n8n..."
/home/durrrrr/.pyenv/shims/python "${SCRIPT_DIR}/Monitoring/ufc_monitor_odds_movement_with_n8n.py" >> "${SCRIPT_DIR}/Monitoring/ufc_monitor_n8n.log" 2>&1

echo "HEALTHCHECK_OK: ufc-odds-monitor-n8n"
echo ""

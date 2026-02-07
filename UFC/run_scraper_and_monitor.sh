#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration flags
SCRAPE_MONEYLINES=true   # Set to false to disable moneylines scraping + monitoring
SCRAPE_TOTALS=false      # Set to false to disable totals scraping + monitoring

# Export flags as environment variables for the monitoring script
export SCRAPE_MONEYLINES
export SCRAPE_TOTALS

date

# Normalize flags to lowercase for consistent checks
SCRAPE_MONEYLINES="${SCRAPE_MONEYLINES,,}"
SCRAPE_TOTALS="${SCRAPE_TOTALS,,}"

# Scrape moneylines if enabled
if [ "$SCRAPE_MONEYLINES" = true ]; then
    echo "Scraping moneylines..."
     /home/durrrrr/.pyenv/shims/python "${SCRIPT_DIR}/Scraping/ufc.py" >> "${SCRIPT_DIR}/Scraping/log.log" 2>&1
else
    echo "Moneylines scraping disabled"
fi

sleep 5

# Scrape totals if enabled
if [ "$SCRAPE_TOTALS" = true ]; then
    echo "Scraping totals..."
    /home/durrrrr/.pyenv/shims/python "${SCRIPT_DIR}/Scraping/ufc_totals.py" >> "${SCRIPT_DIR}/Scraping/log_totals.log" 2>&1
else
    echo "Totals scraping disabled"
fi

sleep 5

# Run monitoring (will automatically skip disabled types)
echo "Running monitoring..."
/home/durrrrr/.pyenv/shims/python "${SCRIPT_DIR}/Monitoring/ufc_monitor_odds_movement.py" >> "${SCRIPT_DIR}/Monitoring/ufc_monitor.log" 2>&1

echo ""

#!/bin/bash

# Configuration flags
SCRAPE_MONEYLINES=true   # Set to false to disable moneylines scraping + monitoring
SCRAPE_TOTALS=false      # Set to false to disable totals scraping + monitoring
TARGET_PROMOTION_KEYWORDS="ufc"  # Comma-separated, no quotes or parentheses
# "pfl", "lfa", "one", "oktagon", "cwfc", "cage-warriors", "rizin", "brave", "ksw", "uaew", "uae-warriors"

# Export flags as environment variables for the monitoring script
export SCRAPE_MONEYLINES
export SCRAPE_TOTALS
export TARGET_PROMOTION_KEYWORDS

date

# Normalize flags to lowercase for consistent checks
SCRAPE_MONEYLINES="${SCRAPE_MONEYLINES,,}"
SCRAPE_TOTALS="${SCRAPE_TOTALS,,}"

# Scrape moneylines if enabled
if [ "$SCRAPE_MONEYLINES" = true ]; then
    echo "Scraping moneylines..."
    /home/trinity/.pyenv/shims/python /home/trinity/odds-monitoring/UFC/Scraping/ufc.py >> /home/trinity/odds-monitoring/UFC/Scraping/log.log 2>&1
else
    echo "Moneylines scraping disabled"
fi

sleep 5

# Scrape totals if enabled
if [ "$SCRAPE_TOTALS" = true ]; then
    echo "Scraping totals..."
    /home/trinity/.pyenv/shims/python /home/trinity/odds-monitoring/UFC/Scraping/ufc_totals.py >> /home/trinity/odds-monitoring/UFC/Scraping/log_totals.log 2>&1
else
    echo "Totals scraping disabled"
fi

sleep 5

# Run monitoring (will automatically skip disabled types)
echo "Running monitoring..."
/home/trinity/.pyenv/shims/python /home/trinity/odds-monitoring/UFC/Monitoring/ufc_monitor_odds_movement.py >> /home/trinity/odds-monitoring/UFC/Monitoring/ufc_monitor.log 2>&1

echo ""

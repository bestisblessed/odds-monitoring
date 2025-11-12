#!/bin/bash

date 

/home/trinity/.pyenv/shims/python /home/trinity/odds-monitoring/UFC/Scraping/ufc.py >> /home/trinity/odds-monitoring/UFC/Scraping/log.log 2>&1
sleep 5
/home/trinity/.pyenv/shims/python /home/trinity/odds-monitoring/UFC/Scraping/ufc_totals.py >> /home/trinity/odds-monitoring/UFC/Scraping/log_totals.log 2>&1
sleep 5
/home/trinity/.pyenv/shims/python /home/trinity/odds-monitoring/UFC/Monitoring/ufc_monitor_odds_movement.py >> /home/trinity/odds-monitoring/UFC/Monitoring/ufc_monitor.log 2>&1

echo ""

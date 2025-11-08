#!/usr/bin/env bash

# Run scraping first
/usr/bin/python3.10 /home/bestisblessed/odds-monitoring/UFC/Scraping/ufc.py

# Run monitoring + n8n
/usr/bin/python3.10 /home/bestisblessed/odds-monitoring/UFC/Monitoring/ufc_monitor_odds_movement_with_n8n.py

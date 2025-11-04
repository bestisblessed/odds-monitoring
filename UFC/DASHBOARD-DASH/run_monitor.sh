#!/bin/bash

# UFC Odds Movement Monitor Script
# This script monitors UFC odds movements and sends Pushover notifications

cd "$(dirname "$0")"

python3 ufc_monitor_odds_movement.py

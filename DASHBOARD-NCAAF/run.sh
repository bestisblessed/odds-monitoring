#!/bin/bash

# Remove existing data directory if it exists
rm -rf data/

# SSH into Neo and create a zip file of NCAAF odds data
# ssh Neo "cd /Users/neo/odds-monitoring && rm -f ncaaf_odds_vsin_2024.zip && if ls data/ncaaf_odds_vsin_2024* 1> /dev/null 2>&1; then zip -v ncaaf_odds_vsin_2024.zip data/ncaaf_odds_vsin_2024*; echo 'NCAAF files zipped successfully'; else echo 'No NCAAF files found matching the pattern'; fi"

# Copy the zip file from Neo to the local machine
scp Neo:/Users/neo/odds-monitoring/ncaaf_odds_vsin_2024.zip .

# Unzip the file
unzip ncaaf_odds_vsin_2024.zip

echo "NCAAF odds data has been retrieved and extracted."

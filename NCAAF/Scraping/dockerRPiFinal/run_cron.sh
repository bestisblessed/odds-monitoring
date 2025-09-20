#!/bin/bash

cd /home/trinity/odds-monitoring/NCAAF/Scraping/dockerRPiFinal

# Run the scraper once
docker run --rm -v /home/trinity/odds-monitoring/NCAAF/Scraping/data:/app/data ncaaf-scraper-rpi

# Convert JSON files to CSV format
python json_to_csv.py

# Log the run
#echo "$(date): NCAAF scraper completed (JSON + CSV files generated)" >> /Users/td/Code/odds-monitoring/NCAAF/Scraping/scraper.log

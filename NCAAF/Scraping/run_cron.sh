#!/bin/bash

cd ~/odds-monitoring/NCAAF/Scraping

# Run the scraper once
docker run --rm -v $(pwd)/data:/app/data ncaaf-scraper-rpi

# Log the run
echo "$(date): NCAAF scraper completed" >> /Users/td/Code/odds-monitoring/NCAAF/Scraping/scraper.log

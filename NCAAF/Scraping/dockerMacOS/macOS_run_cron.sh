#!/bin/bash

cd ~/Code/odds-monitoring/NCAAF/Scraping/dockerMacOS
# # cd ~/odds-monitoring/NCAAF/Scraping

# # Stop any existing container
# docker compose -f docker-compose-macOS.yml down

# # Run the scraper once
# # docker compose -f docker-compose-macOS.yml up --no-deps ncaaf-scraper-macos
# # docker compose -f docker-compose-macOS.yml up -d
# docker compose -f docker-compose-macOS.yml up ncaaf-scraper-macos

# # Clean up after completion
# # docker compose -f docker-compose-macOS.yml down
docker compose -f docker-compose-macOS.yml run --rm ncaaf-scraper-macos

# Log the run
echo "$(date): NCAAF scraper completed" >> /Users/td/Code/odds-monitoring/NCAAF/Scraping/scraper.log

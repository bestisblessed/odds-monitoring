#!/bin/bash

cd ~/odds-monitoring/NCAAF/Scraping/dockerRPi

# # Stop any existing container
# docker-compose down

# # Run the scraper once
# docker-compose up ncaaf-scraper

# # Clean up after completion
# # docker-compose down
docker-compose run --rm ncaaf-scraper

# Log the run
echo "$(date): NCAAF scraper completed" >> ~/odds-monitoring/NCAAF/Scraping/dockerRPi/scraper.log

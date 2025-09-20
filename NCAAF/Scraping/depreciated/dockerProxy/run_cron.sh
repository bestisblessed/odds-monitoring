#!/bin/bash

cd ~/odds-monitoring/NCAAF/Scraping/dockerProxy
echo "$(date): Starting NCAAF scraper with rotating proxies"

# Restart proxy rotator to get fresh proxies
docker-compose restart proxy-rotator
sleep 10

# Run scraper with proxy rotation
docker-compose up --no-deps ncaaf-scraper-rpi

# Log the run
echo "$(date): NCAAF scraper completed with rotating proxies" >> /Users/td/Code/odds-monitoring/NCAAF/Scraping/scraper.log
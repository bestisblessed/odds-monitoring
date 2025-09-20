#!/bin/bash

cd ~/odds-monitoring/NCAAF/Scraping/dockerProxy

echo "Building NCAAF scraper container with proxy rotation..."
docker-compose build

echo "✅ Build completed successfully!"
echo "Starting NCAAF scraper with proxy rotation..."
docker-compose up --no-deps ncaaf-scraper-rpi

echo ""
echo "✅ Container started successfully!"
echo "🎉 NCAAF Scraper just ran with rotating proxies!"

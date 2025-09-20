#!/bin/bash

echo "Building NCAAF scraper container for Raspberry Pi..."
docker build -t ncaaf-scraper-rpi .

echo "✅ Build completed successfully!"
echo "Starting NCAAF scraper for Raspberry Pi..."
docker run --rm -v /home/trinity/odds-monitoring/NCAAF/Scraping/data:/app/data ncaaf-scraper-rpi

echo ""
echo "✅ Container started successfully!"
echo "🎉 NCAAF Scraper just ran!"

# Convert JSON files to CSV format
echo "📊 Converting JSON files to CSV format..."
python /home/trinity/odds-monitoring/NCAAF/Scraping/json_to_csv.py

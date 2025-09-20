#!/bin/bash

echo "Building NCAAF scraper container for Raspberry Pi..."
docker build -t ncaaf-scraper-rpi .

echo "✅ Build completed successfully!"
echo "Starting NCAAF scraper for Raspberry Pi..."
docker run --rm -v $(pwd)/data:/app/data ncaaf-scraper-rpi

echo ""
echo "✅ Container started successfully!"
echo "🎉 NCAAF Scraper just ran!"

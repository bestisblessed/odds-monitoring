#!/bin/bash

echo "Starting NCAAF scraper..."
docker-compose run --rm ncaaf-scraper

if [ $? -eq 0 ]; then
    echo "✅ Container started successfully!"
    echo "Check logs with: ./logs.sh"
    echo "Stop with: ./stop.sh"
else
    echo "❌ Failed to start container!"
    exit 1
fi

#!/bin/bash

# Simple script to build and run the NCAAF scraper

echo "Building NCAAF scraper container..."
docker-compose build

echo "Starting NCAAF scraper..."
# docker-compose up -d
docker-compose run --rm ncaaf-scraper

echo "Container is running! Check logs with: docker-compose logs -f"
echo "Stop with: docker-compose down"

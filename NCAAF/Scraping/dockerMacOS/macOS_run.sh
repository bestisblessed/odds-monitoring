#!/bin/bash

echo "Starting NCAAF scraper for macOS..."
docker compose -f docker-compose-macOS.yml run --rm ncaaf-scraper-macos
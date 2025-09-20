#!/bin/bash

echo "Building NCAAF scraper container for macOS..."
docker compose -f docker-compose-macOS.yml build

echo "✅ Build completed successfully!"
echo "Starting NCAAF scraper for macOS..."
docker compose -f docker-compose-macOS.yml run --rm ncaaf-scraper-macos

echo ""
echo "✅ Container started successfully!"
echo ""
echo "🎉 NCAAF Scraper just ran!"
echo ""


# if [ $? -eq 0 ]; then
#     echo "✅ Build completed successfully!"
#     echo "Starting NCAAF scraper for macOS..."
    
#     # docker compose -f docker-compose-macOS.yml up -d
#     docker compose -f docker-compose-macOS.yml run --rm ncaaf-scraper-macos
    
#     if [ $? -eq 0 ]; then
#         echo "✅ Container started successfully!"
#         echo ""
#         echo "🎉 NCAAF Scraper just ran!"
#         echo ""
#     else
#         echo "❌ Failed to start container!"
#         exit 1
#     fi
# else
#     echo "❌ Build failed!"
#     exit 1
# fi
#!/bin/bash

echo "📋 Step 1: Extracting game URLs with kickoff times..."
python oddschecker_game_id_scraper.py

# Check if game URLs were successfully extracted
if [ -f "data/props/oddschecker_game_urls.csv" ]; then
    echo ""
    echo "🎯 Step 2: Scraping props data from each game..."
    python oddschecker_props_scraper.py
    echo ""
    echo "✅ Scraper execution completed!"
    echo "📁 Check data/props/ for output files:"
    # echo "  - oddschecker_game_urls.csv (game URLs & kickoff times)"
    # echo "  - oddschecker_production_nfl_props_*.csv (props data)"
else
    echo "❌ Game URL extraction failed!"
    echo "💡 Check if OddsChecker is accessible or try again later"
    exit 1
fi

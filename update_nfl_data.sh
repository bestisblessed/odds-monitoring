#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NFL_ANALYSIS_DIR="$SCRIPT_DIR/NFL/Analysis"
NFL_AI_ROOT="$(cd "$SCRIPT_DIR/../nfl-ai" && pwd)"
STREAMLIT_ODDS_DIR="$NFL_AI_ROOT/Websites/Streamlit/data/odds"

# NFL AI Odds Scraper collects on donpablo; refresh locally or pull from it.
source "$SCRIPT_DIR/scripts/odds_runtime.sh"
cd "$SCRIPT_DIR"
if [[ "$ODDS_SOURCE_ROOT" != "$SCRIPT_DIR" ]]; then
    mkdir -p NFL/Scraping/data
    rsync -a --delay-updates "$ODDS_SOURCE_ROOT/NFL/Scraping/data/" NFL/Scraping/data/
fi
current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')
mkdir -p zips
zip -rq "zips/nfl_backup_${current_date}.zip" NFL/Scraping/data/
echo "NFL backup created from local snapshots"

cd "$NFL_ANALYSIS_DIR"
"$PYTHON" nfl_odds_data_processing.py
"$PYTHON" nfl_odds_data_analysis.py

### Copy odds data files to nfl-ai directory ###
mkdir -p "$STREAMLIT_ODDS_DIR"
cp "$NFL_ANALYSIS_DIR/data/nfl_odds_movements.csv" "$STREAMLIT_ODDS_DIR/"
cp "$NFL_ANALYSIS_DIR/data/nfl_odds_movements_circa.csv" "$STREAMLIT_ODDS_DIR/"
cp "$NFL_ANALYSIS_DIR/data/nfl_odds_movements_dk.csv" "$STREAMLIT_ODDS_DIR/"
cp "$NFL_ANALYSIS_DIR/data/nfl_odds_movements.pdf" "$STREAMLIT_ODDS_DIR/"
echo "Copied NFL odds data files to nfl-ai directory"

#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NFL_ANALYSIS_DIR="$SCRIPT_DIR/NFL/Analysis"
NFL_AI_ROOT="$(cd "$SCRIPT_DIR/../nfl-ai" && pwd)"
STREAMLIT_ODDS_DIR="$NFL_AI_ROOT/Websites/Streamlit/data/odds"

### Zip NFL Data ###
current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')
mkdir -p zips
ssh durrrrr "cd /home/durrrrr/odds-monitoring && \
    mkdir -p zips && \
    zip -r zips/nfl_backup_${current_date}.zip NFL/Scraping/data/ && \
    echo 'NFL backup created on durrrrr'"

### Unzip NFL Data ###
current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')
rsync -av durrrrr:/home/durrrrr/odds-monitoring/zips/ zips/
mkdir -p NFL/Scraping/data
unzip -o zips/nfl_backup_${current_date}.zip "NFL/Scraping/data/*" -d ./
echo "Restored: NFL/Scraping/data/"

# DELETE REMOTE NFL ODDS DATA FILES
#ssh durrrrr "rm -rf /home/durrrrr/odds-monitoring/NFL/Scraping/data/* && echo 'Cleared NFL data files on durrrrr'"

cd "$NFL_ANALYSIS_DIR"
python nfl_odds_data_processing.py
python nfl_odds_data_analysis.py

### Copy odds data files to nfl-ai directory ###
mkdir -p "$STREAMLIT_ODDS_DIR"
cp "$NFL_ANALYSIS_DIR/data/nfl_odds_movements.csv" "$STREAMLIT_ODDS_DIR/"
cp "$NFL_ANALYSIS_DIR/data/nfl_odds_movements_circa.csv" "$STREAMLIT_ODDS_DIR/"
cp "$NFL_ANALYSIS_DIR/data/nfl_odds_movements_dk.csv" "$STREAMLIT_ODDS_DIR/"
cp "$NFL_ANALYSIS_DIR/data/nfl_odds_movements.pdf" "$STREAMLIT_ODDS_DIR/"
echo "Copied NFL odds data files to nfl-ai directory"

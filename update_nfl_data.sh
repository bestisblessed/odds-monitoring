#!/bin/bash

### Zip NFL Data ###
current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')
mkdir -p zips
ssh Trinity "cd /home/trinity/odds-monitoring && \
    mkdir -p zips && \
    zip -r zips/nfl_backup_${current_date}.zip NFL/Scraping/data/ && \
    echo 'NFL backup created on Trinity'"

### Unzip NFL Data ###
current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')
rsync -av Trinity:/home/trinity/odds-monitoring/zips/ zips/
mkdir -p NFL/Scraping/data
unzip -o zips/nfl_backup_${current_date}.zip "NFL/Scraping/data/*" -d ./
echo "Restored: NFL/Scraping/data/"

# DELETE REMOTE NFL ODDS DATA FILES
#ssh Trinity "rm -rf /home/trinity/odds-monitoring/NFL/Scraping/data/* && echo 'Cleared NFL data files on Trinity'" 

cd /Users/td/Code/odds-monitoring/NFL/Analysis 
python nfl_odds_data_processing.py
python nfl_odds_data_analysis.py

### Copy odds data files to nfl-ai directory ###
cp /Users/td/Code/odds-monitoring/NFL/Analysis/data/nfl_odds_movements.csv /Users/td/Code/nfl-ai/Websites/Streamlit/data/odds/
cp /Users/td/Code/odds-monitoring/NFL/Analysis/data/nfl_odds_movements_circa.csv /Users/td/Code/nfl-ai/Websites/Streamlit/data/odds/
cp /Users/td/Code/odds-monitoring/NFL/Analysis/data/nfl_odds_movements_dk.csv /Users/td/Code/nfl-ai/Websites/Streamlit/data/odds/
cp /Users/td/Code/odds-monitoring/NFL/Analysis/data/nfl_odds_movements.pdf /Users/td/Code/nfl-ai/Websites/Streamlit/data/odds/
echo "Copied NFL odds data files to nfl-ai directory"
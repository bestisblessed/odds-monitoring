#!/bin/bash

### Zip UFC Data ###
current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')
mkdir -p zips
ssh Trinity "cd /home/trinity/odds-monitoring && \
    mkdir -p zips && \
    zip -r zips/ufc_backup_${current_date}.zip UFC/Scraping/data/ && \
    echo 'UFC backup created on Trinity'"

### Unzip UFC Data ###
current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')
rsync -av Trinity:/home/trinity/odds-monitoring/zips/ zips/
mkdir -p UFC/Scraping/data
unzip -o zips/ufc_backup_${current_date}.zip "UFC/Scraping/data/*" -d ./
echo "Restored: UFC/Scraping/data/"

### PROCESS ODDS DATA AND COPY TO STREAMLIT $ SWIFT APP
cd ~/Code/odds-monitoring/UFC/Analysis
python ufc_odds_data_processing_fightoddsio.py
cp /Users/td/Code/odds-monitoring/UFC/Analysis/data/ufc_odds_movements_fightoddsio.csv ~/Code/mma-ai-swift-app/data/
echo "Copying to swift app server.."
scp /Users/td/Code/odds-monitoring/UFC/Analysis/data/ufc_odds_movements_fightoddsio.csv Trinity:/home/trinity/mma-ai-swift-app/data/
#git add data/ufc_odds_movements_fightoddsio.csv -f
#git commit -m "update odds data"
#git push


# DELETE REMOTE UFC ODDS DATA FILES
#ssh Trinity "rm -rf /home/trinity/odds-monitoring/UFC/Scraping/data/* && echo 'Cleared UFC data files on Trinity'"
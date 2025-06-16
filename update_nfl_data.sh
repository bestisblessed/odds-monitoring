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
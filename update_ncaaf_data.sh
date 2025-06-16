#!/bin/bash

### Zip NCAAF Data ###
current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')
mkdir -p zips
ssh Trinity "cd /home/trinity/odds-monitoring && \
    mkdir -p zips && \
    zip -r zips/ncaaf_backup_${current_date}.zip NCAAF/Scraping/data/ && \
    echo 'NCAAF backup created on Trinity'"

### Unzip NCAAF Data ###
current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')
rsync -av Trinity:/home/trinity/odds-monitoring/zips/ zips/
mkdir -p NCAAF/Scraping/data
unzip -o zips/ncaaf_backup_${current_date}.zip "NCAAF/Scraping/data/*" -d ./
echo "Restored: NCAAF/Scraping/data/"

# DELETE REMOTE NCAAF ODDS DATA FILES
#ssh Trinity "rm -rf /home/trinity/odds-monitoring/NCAAF/Scraping/data/* && echo 'Cleared NCAAF data files on Trinity'" 
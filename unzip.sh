#!/bin/bash

current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')

# scp -r Trinity:/home/trinity/odds-monitoring/zips .
rsync -av Trinity:/home/trinity/odds-monitoring/zips/ zips/

mkdir -p NFL/Scraping/data
mkdir -p UFC/Scraping/data
mkdir -p NCAAF/Scraping/data

unzip -o zips/nfl_backup_${current_date}.zip "NFL/Scraping/data/*" -d ./
unzip -o zips/ufc_backup_${current_date}.zip "UFC/Scraping/data/*" -d ./
unzip -o zips/ncaaf_backup_${current_date}.zip "NCAAF/Scraping/data/*" -d ./

echo "Restored: NFL/Scraping/data/"
echo "Restored: UFC/Scraping/data/"
echo "Restored: NCAAF/Scraping/data/"
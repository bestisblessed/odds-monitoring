#!/bin/bash

current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')

mkdir -p zips

# Create zip file for all data
# zip -r zips/data_backup_${current_date}.zip data
# echo "Backup created: zips/data_backup_${current_date}.zip"

# Create zip files for each sport's entire data directory
# zip -r zips/nfl_backup_${current_date}.zip NFL/Scraping/data/
# zip -r zips/ufc_backup_${current_date}.zip UFC/Scraping/data/
# zip -r zips/ncaaf_backup_${current_date}.zip NCAAF/Scraping/data/
# echo "Backup created: zips/nfl_backup_${current_date}.zip"
# echo "Backup created: zips/ufc_backup_${current_date}.zip"
# echo "Backup created: zips/ncaaf_backup_${current_date}.zip"

# SSH into Trinity and create the backups directly there
ssh Trinity "cd /home/trinity/odds-monitoring && \
    mkdir -p zips && \
    zip -r zips/nfl_backup_${current_date}.zip NFL/Scraping/data/ && \
    zip -r zips/ufc_backup_${current_date}.zip UFC/Scraping/data/ && \
    zip -r zips/ncaaf_backup_${current_date}.zip NCAAF/Scraping/data/ && \
    echo 'Backups created on Trinity'"
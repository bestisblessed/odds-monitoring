#!/bin/bash

#current_date=$(date +%^b_%d_%y)
current_date=$(date +%b_%d_%y | tr '[:lower:]' '[:upper:]')

mkdir -p zips
zip -r zips/data_backup_${current_date}.zip data
echo "Backup created: zips/data_backup_${current_date}.zip"

# Create zip files for each sport based on file naming convention
zip -r zips/ufc_backup_${current_date}.zip data/ufc_odds_vsin_*.json
zip -r zips/ncaaf_backup_${current_date}.zip data/ncaaf_odds_vsin_*.json
zip -r zips/nfl_backup_${current_date}.zip data/nfl_odds_vsin_*.json
echo "Backup created: zips/ufc_backup_${current_date}.zip"
echo "Backup created: zips/ncaaf_backup_${current_date}.zip"
echo "Backup created: zips/nfl_backup_${current_date}.zip"

#!/bin/bash

#./update_data.sh
cd UFC/Analysis
python ufc_odds_data_processing_fightoddsio.py

cd ~/Code/mma-ai/Streamlit
cp /Users/td/Code/odds-monitoring/UFC/Analysis/data/ufc_odds_movements_fightoddsio.csv data/
#git add data/ufc_odds_movements_fightoddsio.csv -f
#git commit -m "update odds data"
#git push

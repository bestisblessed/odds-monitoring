#!/bin/bash

rm -rf data
rm data_backup.zip

# ssh Neo "zip -r /Users/neo/odds-monitoring/data_backup.zip /Users/neo/odds-monitoring/data"
#ssh Neo "cd /Users/neo/odds-monitoring/ && rm data_backup.zip && zip -r data_backup.zip data"
ssh Neo "cd /Users/neo/odds-monitoring/ && zip -r data_backup.zip data"

scp -r Neo:~/odds-monitoring/data_backup.zip .
unzip data_backup.zip -d .
#scp -r Neo:~/odds-monitoring/data .

echo ''

python nfl_monitor_odds_movement.py

echo ''

echo "1. Now, manually run 'app.py' by executing: python app.py"
echo "2. After that, manually run 'dashboard.py' by executing: python dashboard.py"
echo "Once both scripts are running, you can access the app at http://127.0.0.1:8050"

#!/bin/bash

rm -rf data/
# mkdir -p data/odds/

ssh Neo "cd /Users/neo/odds-monitoring && rm nfl_odds_vsin_2024.zip && if ls data/nfl_odds_vsin_2024* 1> /dev/null 2>&1; then zip -v nfl_odds_vsin_2024.zip data/nfl_odds_vsin_2024*; echo 'Files zipped successfully'; else echo 'No files found matching the pattern'; fi"
scp Neo:/Users/neo/odds-monitoring/nfl_odds_vsin_2024.zip .
unzip nfl_odds_vsin_2024.zip

# rm data_backup.zip
# scp -r Neo:/Users/neo/odds-monitoring/data/ data/odds/

# ssh Neo "zip -r /Users/neo/odds-monitoring/data_backup.zip /Users/neo/odds-monitoring/data"
#ssh Neo "cd /Users/neo/odds-monitoring/ && rm data_backup.zip && zip -r data_backup.zip data"
# ssh Neo "cd /Users/neo/odds-monitoring/ && zip -r data_backup.zip data"
# scp -r Neo:~/odds-monitoring/data_backup.zip .
# unzip data_backup.zip -d data/odds/ && mv data/odds/data/* data/odds/ && rmdir data/odds/data
# unzip data_backup.zip -d data/odds/
#scp -r Neo:~/odds-monitoring/data .

echo ''

python nfl_monitor_odds_movement.py

echo ''

echo "1. Now, manually run 'app.py' by executing: python app.py"
echo "2. After that, manually run 'dashboard.py' by executing: python dashboard.py"
echo "Once both scripts are running, you can access the app at http://127.0.0.1:8050"

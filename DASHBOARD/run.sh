#!/bin/bash

scp -r Neo:~/odds-monitoring/data .

python monitor_odds_movement.py

echo "1. Now, manually run 'app.py' by executing: python app.py"
echo "2. After that, manually run 'dashboard.py' by executing: python dashboard.py"
echo "Once both scripts are running, you can access the app at http://127.0.0.1:8050"
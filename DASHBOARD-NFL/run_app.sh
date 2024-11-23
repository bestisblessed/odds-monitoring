#!/bin/bash

# Start app.py in a new screen session called "app"
screen -dmS app bash -c "python app.py; exec bash"

# Start dashboard.py in a new screen session called "dashboard"
screen -dmS dashboard bash -c "python dashboard.py; exec bash"

echo "Both app.py and dashboard.py are running in separate named screen sessions."

# To attach to the sessions
screen -ls
echo "Use 'screen -r app' or 'screen -r dashboard' to attach to the sessions."

sleep 2

screen -r dashboard
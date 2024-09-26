#!/bin/bash

scp -r Neo:~/odds-monitoring/data .

python monitor_odds_movement.py
#!/bin/bash

# Run zip and unzip operations
./zip.sh
./unzip.sh

# Change directory to NFL/Analysis
cd NFL/Analysis || {
    echo "Error: Could not change to NFL/Analysis directory"
    exit 1
}

# Run the Python script
python nfl_odds_data_processing.py || {
    echo "Error: Python script execution failed"
    exit 1
} 
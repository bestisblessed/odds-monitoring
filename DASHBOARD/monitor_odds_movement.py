import json
import os
import re

# Get the absolute directory containing the odds files dynamically
directory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))

# Function to dynamically load JSON files based on timestamps
def load_files(directory):
    # Use regex to extract datetime from filenames (assuming filenames follow the same pattern)
    files = [f for f in os.listdir(directory) if re.match(r'nfl_odds_vsin_\d{8}_\d{4}\.json', f)]
    # Sort files by datetime in the filename
    files.sort(key=lambda x: re.findall(r'(\d{8}_\d{4})', x)[0])
    return files

# Function to format odds (to deal with multiline strings for favorite/underdog odds)
def format_odds(odds):
    return odds.replace("\n", " | ")

# Function to compare odds between two datasets and include the date in the output
def detect_odds_movement(odds_before, odds_after):
    movements = []
    
    # Loop through games in odds_before
    for game_before, game_after in zip(odds_before, odds_after):
        if game_before['Time'] == game_after['Time']:  # Match games by time
            
            # Extract the date from the second column (column name)
            game_date_column_name = list(game_before.keys())[1]  # The actual column name for the date
            
            # Compare odds from different sportsbooks
            for key in game_before:
                if key not in ["Time", game_date_column_name] and key in game_after:
                    if game_before[key] != game_after[key]:  # Check if odds have changed
                        movements.append({
                            'game_time': game_before['Time'],
                            'game_date_column_name': game_date_column_name,  # Save the actual column name
                            'game_date_value': game_before[game_date_column_name],  # Save the value of the date column
                            'sportsbook': key,
                            'odds_before': format_odds(game_before[key]),
                            'odds_after': format_odds(game_after[key])
                        })
    return movements

# Load and sort files
files = load_files(directory)

# Loop through consecutive files and compare odds
for i in range(len(files) - 1):
    file1 = files[i]
    file2 = files[i + 1]
    
    with open(os.path.join(directory, file1)) as f1, open(os.path.join(directory, file2)) as f2:
        odds_before = json.load(f1)
        odds_after = json.load(f2)
    
    # Detect movements between consecutive files
    odds_movements = detect_odds_movement(odds_before, odds_after)
    
    # Output movements
    if odds_movements:
        print(f"\nODDS MOVEMENT DETECTED {file1} and {file2}:\n")
        for movement in odds_movements:
            print(f"Game Date Column: {movement['game_date_column_name']}")
            print(f"Matchup: {movement['game_date_value'].replace('\n', ' vs').strip()}")
            print(f"Sportsbook: {movement['sportsbook']}")
            print(f"Odds before: {movement['odds_before']}")
            print(f"Odds after: {movement['odds_after']}")
            print("")
    else:
        print(f"No odds movement detected between {file1} and {file2}.")

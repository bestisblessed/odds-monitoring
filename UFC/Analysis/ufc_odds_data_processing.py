import os
import re
import json
import csv  # Importing the csv module
import shutil
from datetime import datetime, timedelta

shutil.copytree('../Scraping/data', 'data', dirs_exist_ok=True)

# Delete empty files right at the beginning
files = os.listdir('data')
for file in files:
    file_path = os.path.join('data', file)
    if os.path.isfile(file_path) and os.stat(file_path).st_size == 0:
        print(f"Deleting empty file: {file}")
        os.remove(file_path)

# Function to dynamically load JSON files based on timestamps
def load_files(directory):
    files = [f for f in os.listdir(directory) if re.match(r'ufc_odds_vsin_\d{8}_\d{4}\.json', f)]
    files.sort(key=lambda x: re.findall(r'(\d{8}_\d{4})', x)[0])
    return files

# Function to format odds
def format_odds(odds):
    return odds.replace("\n", " | ")

# Function to compare odds between two datasets
def detect_odds_movement(odds_before, odds_after):
    movements = []
    
    for game_before, game_after in zip(odds_before, odds_after):
        if game_before['Time'] == game_after['Time']:
            game_date_column_name = list(game_before.keys())[1]  # Assuming the second key is the date
            
            for key in game_before:
                if key not in ["Time", game_date_column_name] and key in game_after:
                    if game_before[key] != game_after[key]:
                        movements.append({
                            'game_time': game_before['Time'],  # Game time is stored
                            'game_date_column_name': game_date_column_name,
                            'game_date_value': game_before[game_date_column_name],
                            'sportsbook': key,
                            'odds_before': format_odds(game_before[key]),
                            'odds_after': format_odds(game_after[key])
                        })
    return movements

# Directory containing the odds files
directory = 'data/'

# Load and sort files
files = load_files(directory)

# List to hold all detected movements for CSV
all_movements = []

# Loop through consecutive files and compare odds
for i in range(len(files) - 1):
    file1 = files[i]
    file2 = files[i + 1]
    
    with open(os.path.join(directory, file1)) as f1, open(os.path.join(directory, file2)) as f2:
        odds_before = json.load(f1)
        odds_after = json.load(f2)
# # Loop through consecutive files and compare odds
# for i in range(len(files) - 1):
#     file1 = files[i]
#     file2 = files[i + 1]
    
#     with open(os.path.join(directory, file1)) as f1, open(os.path.join(directory, file2)) as f2:
#         # Check if the files are empty before loading them
#         if os.stat(f1.name).st_size == 0:
#             print(f"File {f1.name} is empty.")
#             continue

#         if os.stat(f2.name).st_size == 0:
#             print(f"File {f2.name} is empty.")
#             continue
        
#         odds_before = json.load(f1)
#         odds_after = json.load(f2)
  
    # Detect movements between consecutive files
    odds_movements = detect_odds_movement(odds_before, odds_after)
    
    if odds_movements:
        for movement in odds_movements:
            all_movements.append({
                'file1': file1,
                'file2': file2,
                'game_date': movement['game_date_column_name'],  # Save the matchup column name
                'game_time': movement['game_time'],  # Use game_time directly
                'matchup': f"{movement['game_date_value'].replace('\n', ' vs').strip()}",
                'sportsbook': movement['sportsbook'],
                'odds_before': movement['odds_before'],
                'odds_after': movement['odds_after']
            })
    else:
        # print(f"No odds movement detected between {file1} and {file2}.")
        pass

# Save movements to a CSV file
csv_file_path = 'data/ufc_odds_movements.csv'
with open(csv_file_path, mode='w', newline='') as csv_file:
    fieldnames = ['file1', 'file2', 'game_date', 'game_time', 'matchup', 'sportsbook', 'odds_before', 'odds_after']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

    writer.writeheader()  # Write the header
    for movement in all_movements:
        writer.writerow(movement)  # Write each movement

print(f"Odds movements saved to {csv_file_path}")

# Get the dates for our window
current_date = datetime.now()
one_week_ago = current_date - timedelta(weeks=1)
eight_weeks_later = current_date + timedelta(weeks=8)

# Read the CSV file and filter rows based on 'game_date'
filtered_rows = []
with open(csv_file_path, mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    fieldnames = csv_reader.fieldnames
    for row in csv_reader:
        try:
            # Parse the date string (e.g., 'Sat,December 14th')
            date_str = row['game_date'].replace('th', '').replace('nd', '').replace('rd', '').replace('st', '')
            row_date = datetime.strptime(date_str, '%a,%B %d')
            
            # Set year to current year, or next year if the date has already passed this year
            row_date = row_date.replace(year=current_date.year)
            if row_date < one_week_ago:
                row_date = row_date.replace(year=current_date.year + 1)
            
            # Keep only if date is within our window (last week to 8 weeks ahead)
            if one_week_ago <= row_date <= eight_weeks_later:
                filtered_rows.append(row)
        except ValueError as e:
            print(f"Skipping row due to date parsing error: {row['game_date']}")
            continue

# Write the filtered rows back to the CSV file
with open(csv_file_path, mode='w', newline='') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    for row in filtered_rows:
        writer.writerow(row)

print("Rows with dates from the past week to 8 weeks ahead have been saved back to ufc_odds_movements.csv")

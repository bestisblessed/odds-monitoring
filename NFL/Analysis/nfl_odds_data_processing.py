import os
import re
import json
import csv
import pandas as pd
from datetime import datetime
import shutil

shutil.copytree('../Scraping/data', 'data', dirs_exist_ok=True)

files = os.listdir('data/odds/')
for file in files:
    file_path = os.path.join('data/odds/', file)
    if os.path.isfile(file_path) and os.stat(file_path).st_size == 0:
        print(f"Deleting empty file: {file}")
        os.remove(file_path)
def load_files(directory):
    files = [f for f in os.listdir(directory) if re.match(r'nfl_odds_vsin_\d{8}_\d{4}\.json', f)]
    files.sort(key=lambda x: re.findall(r'(\d{8}_\d{4})', x)[0])
    return files
def format_odds(odds):
    return odds.replace("\n", " | ")
def detect_odds_movement(odds_before, odds_after):
    movements = []
    for game_before, game_after in zip(odds_before, odds_after):
        if game_before['Time'] == game_after['Time']:
            game_date_column_name = list(game_before.keys())[1]  
            for key in game_before:
                if key not in ["Time", game_date_column_name] and key in game_after:
                    if game_before[key] != game_after[key]:
                        movements.append({
                            'game_time': game_before['Time'],  
                            'game_date_column_name': game_date_column_name,
                            'game_date_value': game_before[game_date_column_name],
                            'sportsbook': key,
                            'odds_before': format_odds(game_before[key]),
                            'odds_after': format_odds(game_after[key])
                        })
    return movements
directory = 'data/odds/'
files = load_files(directory)
all_movements = []
for i in range(len(files) - 1):
    file1 = files[i]
    file2 = files[i + 1]
    with open(os.path.join(directory, file1)) as f1, open(os.path.join(directory, file2)) as f2:
        odds_before = json.load(f1)
        odds_after = json.load(f2)
    odds_movements = detect_odds_movement(odds_before, odds_after)
    if odds_movements:
        for movement in odds_movements:
            all_movements.append({
                'file1': file1,
                'file2': file2,
                'game_date': movement['game_date_column_name'],  
                'game_time': movement['game_time'],  
                'matchup': f"{movement['game_date_value'].replace('\n', ' vs').strip()}",
                'sportsbook': movement['sportsbook'],
                'odds_before': movement['odds_before'],
                'odds_after': movement['odds_after']
            })
    else:
        pass
csv_file_path = 'data/nfl_odds_movements.csv'
with open(csv_file_path, mode='w', newline='') as csv_file:
    fieldnames = ['file1', 'file2', 'game_date', 'game_time', 'matchup', 'sportsbook', 'odds_before', 'odds_after']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()  
    for movement in all_movements:
        writer.writerow(movement)  
print(f"Odds movements saved to {csv_file_path}")
file_path = 'data/nfl_odds_movements.csv'  
nfl_odds_data = pd.read_csv(file_path)
nfl_odds_data[['team_1', 'team_2']] = nfl_odds_data['matchup'].str.split(' vs ', expand=True)
nfl_odds_data[['team1_odds_before', 'team2_odds_before']] = nfl_odds_data['odds_before'].str.split(r'\s+\|\s+', expand=True)
nfl_odds_data[['team1_odds_after', 'team2_odds_after']] = nfl_odds_data['odds_after'].str.split(r'\s+\|\s+', expand=True)
nfl_odds_data['team1_odds_before'] = nfl_odds_data['team1_odds_before'].str.split().str[0]
nfl_odds_data['team2_odds_before'] = nfl_odds_data['team2_odds_before'].str.split().str[0]
nfl_odds_data['team1_odds_after'] = nfl_odds_data['team1_odds_after'].str.split().str[0]
nfl_odds_data['team2_odds_after'] = nfl_odds_data['team2_odds_after'].str.split().str[0]
def extract_timestamp(filename):
    try:
        timestamp_str = filename.split('_')[-1].replace('.json', '')
        return datetime.strptime(filename.split('_')[-2] + "_" + timestamp_str, '%Y%m%d_%H%M')
    except:
        return None
nfl_odds_data['time_before'] = nfl_odds_data['file1'].apply(extract_timestamp)
nfl_odds_data['time_after'] = nfl_odds_data['file2'].apply(extract_timestamp)
nfl_odds_data['time_before'] = nfl_odds_data['time_before'].apply(lambda dt: dt.strftime('%b %d %-I:%M%p') if pd.notnull(dt) else None)
nfl_odds_data['time_after'] = nfl_odds_data['time_after'].apply(lambda dt: dt.strftime('%b %d %-I:%M%p') if pd.notnull(dt) else None)
# nfl_odds_data = nfl_odds_data.drop(columns=['odds_before', 'odds_after', 'file1', 'file2'])
print(nfl_odds_data[['team_1', 'team_2', 'team1_odds_before', 'team2_odds_before', 'team1_odds_after', 'team2_odds_after']].head())
nfl_odds_data = nfl_odds_data.map(lambda x: x.strip() if isinstance(x, str) else x)
nfl_odds_data.to_csv(file_path, index=False)  
nfl_odds_data = pd.read_csv('data/nfl_odds_movements.csv')
circa_odds_data = nfl_odds_data[nfl_odds_data['sportsbook'] == 'Circa']
circa_odds_data = circa_odds_data.map(lambda x: x.strip() if isinstance(x, str) else x)
circa_odds_data.to_csv('data/nfl_odds_movements_circa.csv', index=False)
nfl_odds_data = pd.read_csv('data/nfl_odds_movements.csv')
dk_odds_data = nfl_odds_data[nfl_odds_data['sportsbook'] == 'DK']
dk_odds_data = dk_odds_data.map(lambda x: x.strip() if isinstance(x, str) else x)
dk_odds_data.to_csv('data/nfl_odds_movements_dk.csv', index=False)



### Filter dates ###
import pandas as pd
from datetime import datetime, timedelta
import os
import glob

print("\nExample format: 20241223 (for Dec 23, 2024)")
starter_date_default = '20241223'
current_date = datetime.now().strftime('%Y%m%d')

# Get start date with default
start_date = input(f"Enter start date (YYYYMMDD) [press Enter for {starter_date_default}]: ").strip()
if not start_date:
    start_date = starter_date_default

# Get end date with default (1 week after start date)
start_dt = datetime.strptime(start_date, '%Y%m%d')
default_end = (start_dt + timedelta(days=7)).strftime('%Y%m%d')
end_date = input(f"Enter end date (YYYYMMDD) [press Enter for {default_end}]: ").strip()
if not end_date:
    end_date = default_end

# Validate dates
datetime.strptime(start_date, '%Y%m%d')
datetime.strptime(end_date, '%Y%m%d')

# Files to process
input_files = {
    'all': 'data/nfl_odds_movements.csv',
    'circa': 'data/nfl_odds_movements_circa.csv',
    'dk': 'data/nfl_odds_movements_dk.csv'
}

# Process each file
for name, file_path in input_files.items():
    # Read and filter data
    df = pd.read_csv(file_path)
    df['date'] = df['file1'].str.extract(r'(\d{8})')
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    df = df.drop('date', axis=1)
    
    # Save back to original file
    df.to_csv(file_path, index=False)
    print(f"Filtered {name} odds data saved to {file_path} ({len(df)} rows)")

# Ask about cleaning up raw files
cleanup = input("\nRemove raw odds files from data/odds/? (y/n): ").lower().strip()
if cleanup == 'y':
    # Get all JSON files in the odds directory
    odds_files = glob.glob('data/odds/nfl_odds_vsin_*.json')
    removed = 0
    
    for file in odds_files:
        # Extract date from filename
        file_date = file.split('_')[-2]  # Gets YYYYMMDD from filename
        
        # Remove if outside date range
        if file_date < start_date or file_date > end_date:
            os.remove(file)
            removed += 1
    
    print(f"\nRemoved {removed} raw odds files outside the date range {start_date} to {end_date}") 
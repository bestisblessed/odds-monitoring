# import os
# import re
# import json
# import csv  # Importing the csv module

# # Delete empty files right at the beginning
# files = os.listdir('data')
# for file in files:
#     file_path = os.path.join('data', file)
#     if os.path.isfile(file_path) and os.stat(file_path).st_size == 0:
#         print(f"Deleting empty file: {file}")
#         os.remove(file_path)

# # Function to dynamically load JSON files based on timestamps
# def load_files(directory):
#     files = [f for f in os.listdir(directory) if re.match(r'ncaaf_odds_vsin_\d{8}_\d{4}\.json', f)]
#     files.sort(key=lambda x: re.findall(r'(\d{8}_\d{4})', x)[0])
#     return files

# # Function to format odds
# def format_odds(odds):
#     return odds.replace("\n", " | ")

# # Function to compare odds between two datasets
# def detect_odds_movement(odds_before, odds_after):
#     movements = []
    
#     for game_before, game_after in zip(odds_before, odds_after):
#         if game_before['Time'] == game_after['Time']:
#             game_date_column_name = list(game_before.keys())[1]  # Assuming the second key is the date
            
#             for key in game_before:
#                 if key not in ["Time", game_date_column_name] and key in game_after:
#                     if game_before[key] != game_after[key]:
#                         movements.append({
#                             'game_time': game_before['Time'],  # Game time is stored
#                             'game_date_column_name': game_date_column_name,
#                             'game_date_value': game_before[game_date_column_name],
#                             'sportsbook': key,
#                             'odds_before': format_odds(game_before[key]),
#                             'odds_after': format_odds(game_after[key])
#                         })
#     return movements

# # Directory containing the odds files
# directory = 'data/'

# # Load and sort files
# files = load_files(directory)

# # List to hold all detected movements for CSV
# all_movements = []

# # Loop through consecutive files and compare odds
# for i in range(len(files) - 1):
#     file1 = files[i]
#     file2 = files[i + 1]
    
#     with open(os.path.join(directory, file1)) as f1, open(os.path.join(directory, file2)) as f2:
#         odds_before = json.load(f1)
#         odds_after = json.load(f2)
# # # Loop through consecutive files and compare odds
# # for i in range(len(files) - 1):
# #     file1 = files[i]
# #     file2 = files[i + 1]
    
# #     with open(os.path.join(directory, file1)) as f1, open(os.path.join(directory, file2)) as f2:
# #         # Check if the files are empty before loading them
# #         if os.stat(f1.name).st_size == 0:
# #             print(f"File {f1.name} is empty.")
# #             continue

# #         if os.stat(f2.name).st_size == 0:
# #             print(f"File {f2.name} is empty.")
# #             continue
        
# #         odds_before = json.load(f1)
# #         odds_after = json.load(f2)
  
#     # Detect movements between consecutive files
#     odds_movements = detect_odds_movement(odds_before, odds_after)
    
#     if odds_movements:
#         for movement in odds_movements:
#             all_movements.append({
#                 'file1': file1,
#                 'file2': file2,
#                 'game_date': movement['game_date_column_name'],  # Save the matchup column name
#                 'game_time': movement['game_time'],  # Use game_time directly
#                 'matchup': f"{movement['game_date_value'].replace('\n', ' vs').strip()}",
#                 'sportsbook': movement['sportsbook'],
#                 'odds_before': movement['odds_before'],
#                 'odds_after': movement['odds_after']
#             })
#     else:
#         # print(f"No odds movement detected between {file1} and {file2}.")
#         pass

# # Save movements to a CSV file
# csv_file_path = 'data/ncaaf_odds_movements.csv'
# with open(csv_file_path, mode='w', newline='') as csv_file:
#     fieldnames = ['file1', 'file2', 'game_date', 'game_time', 'matchup', 'sportsbook', 'odds_before', 'odds_after']
#     writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

#     writer.writeheader()  # Write the header
#     for movement in all_movements:
#         writer.writerow(movement)  # Write each movement

# print(f"Odds movements saved to {csv_file_path}")
import os
import re
import json
import csv
import pandas as pd
from datetime import datetime

files = os.listdir('data')
for file in files:
    file_path = os.path.join('data', file)
    if os.path.isfile(file_path) and os.stat(file_path).st_size == 0:
        print(f"Deleting empty file: {file}")
        os.remove(file_path)
def load_files(directory):
    files = [f for f in os.listdir(directory) if re.match(r'ncaaf_odds_vsin_\d{8}_\d{4}\.json', f)]
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
directory = 'data/'
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
csv_file_path = 'data/ncaaf_odds_movements.csv'
with open(csv_file_path, mode='w', newline='') as csv_file:
    fieldnames = ['file1', 'file2', 'game_date', 'game_time', 'matchup', 'sportsbook', 'odds_before', 'odds_after']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()  
    for movement in all_movements:
        writer.writerow(movement)  
print(f"Odds movements saved to {csv_file_path}")
file_path = 'data/ncaaf_odds_movements.csv'  
ncaaf_odds_data = pd.read_csv(file_path)
ncaaf_odds_data[['team_1', 'team_2']] = ncaaf_odds_data['matchup'].str.split(' vs ', expand=True)
ncaaf_odds_data[['team1_odds_before', 'team2_odds_before']] = ncaaf_odds_data['odds_before'].str.split(r'\s+\|\s+', expand=True)
ncaaf_odds_data[['team1_odds_after', 'team2_odds_after']] = ncaaf_odds_data['odds_after'].str.split(r'\s+\|\s+', expand=True)
ncaaf_odds_data['team1_odds_before'] = ncaaf_odds_data['team1_odds_before'].str.split().str[0]
ncaaf_odds_data['team2_odds_before'] = ncaaf_odds_data['team2_odds_before'].str.split().str[0]
ncaaf_odds_data['team1_odds_after'] = ncaaf_odds_data['team1_odds_after'].str.split().str[0]
ncaaf_odds_data['team2_odds_after'] = ncaaf_odds_data['team2_odds_after'].str.split().str[0]
def extract_timestamp(filename):
    try:
        timestamp_str = filename.split('_')[-1].replace('.json', '')
        return datetime.strptime(filename.split('_')[-2] + "_" + timestamp_str, '%Y%m%d_%H%M')
    except:
        return None
ncaaf_odds_data['time_before'] = ncaaf_odds_data['file1'].apply(extract_timestamp)
ncaaf_odds_data['time_after'] = ncaaf_odds_data['file2'].apply(extract_timestamp)
ncaaf_odds_data['time_before'] = ncaaf_odds_data['time_before'].apply(lambda dt: dt.strftime('%b %d %-I:%M%p') if pd.notnull(dt) else None)
ncaaf_odds_data['time_after'] = ncaaf_odds_data['time_after'].apply(lambda dt: dt.strftime('%b %d %-I:%M%p') if pd.notnull(dt) else None)
# ncaaf_odds_data = ncaaf_odds_data.drop(columns=['odds_before', 'odds_after', 'file1', 'file2'])
print(ncaaf_odds_data[['team_1', 'team_2', 'team1_odds_before', 'team2_odds_before', 'team1_odds_after', 'team2_odds_after']].head())
ncaaf_odds_data = ncaaf_odds_data.map(lambda x: x.strip() if isinstance(x, str) else x)
ncaaf_odds_data.to_csv(file_path, index=False)  
ncaaf_odds_data = pd.read_csv('data/ncaaf_odds_movements.csv')
circa_odds_data = ncaaf_odds_data[ncaaf_odds_data['sportsbook'] == 'Circa']
circa_odds_data = circa_odds_data.map(lambda x: x.strip() if isinstance(x, str) else x)
circa_odds_data.to_csv('data/ncaaf_odds_movements_circa.csv', index=False)
ncaaf_odds_data = pd.read_csv('data/ncaaf_odds_movements.csv')
dk_odds_data = ncaaf_odds_data[ncaaf_odds_data['sportsbook'] == 'DK']
dk_odds_data = dk_odds_data.map(lambda x: x.strip() if isinstance(x, str) else x)
dk_odds_data.to_csv('data/ncaaf_odds_movements_dk.csv', index=False)
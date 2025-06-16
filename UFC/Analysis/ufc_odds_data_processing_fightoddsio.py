import os
import re
import csv
import shutil
shutil.copytree('../Scraping/data', 'data', dirs_exist_ok=True)
files = os.listdir('data')
# for file in files:
#     file_path = os.path.join('data', file)
#     if os.path.isfile(file_path) and os.stat(file_path).st_size == 0:
#         print(f"Deleting empty file: {file}")
#         os.remove(file_path)

def load_files(directory):
    files = [f for f in os.listdir(directory) if re.match(r'ufc_odds_fightoddsio_\d{8}_\d{4}\.csv', f)]
    files.sort(key=lambda x: re.findall(r'(\d{8}_\d{4})', x)[0])
    return files

def detect_odds_movement(odds_before, odds_after):
    movements = []
    for fighter_before, fighter_after in zip(odds_before, odds_after):
        if fighter_before['Fighters'] == fighter_after['Fighters']:
            for sportsbook in fighter_before:
                # Skip the 'Fighters' column and 'Event' column if present
                if sportsbook in ['Fighters', 'Event']:
                    continue
                    
                # Check if the sportsbook exists in both datasets and has different values
                if (sportsbook in fighter_after and 
                    fighter_before[sportsbook] and fighter_after[sportsbook] and  # Ensure values are not empty
                    fighter_before[sportsbook] != fighter_after[sportsbook]):
                    movements.append({
                        'fighter': fighter_before['Fighters'],
                        'sportsbook': sportsbook,
                        'odds_before': fighter_before[sportsbook],
                        'odds_after': fighter_after[sportsbook]
                    })
    return movements

directory = 'data/'
files = load_files(directory)
all_movements = []

for i in range(len(files) - 1):
    file1 = files[i]
    file2 = files[i + 1]
    with open(os.path.join(directory, file1)) as f1, open(os.path.join(directory, file2)) as f2:
        odds_before = list(csv.DictReader(f1))
        odds_after = list(csv.DictReader(f2))
    odds_movements = detect_odds_movement(odds_before, odds_after)
    if odds_movements:
        for movement in odds_movements:
            all_movements.append({
                'file1': file1,
                'file2': file2,
                'fighter': movement['fighter'],
                'sportsbook': movement['sportsbook'],
                'odds_before': movement['odds_before'],
                'odds_after': movement['odds_after']
            })

csv_file_path = 'data/ufc_odds_movements_fightoddsio.csv'
with open(csv_file_path, mode='w', newline='') as csv_file:
    fieldnames = ['file1', 'file2', 'fighter', 'sportsbook', 'odds_before', 'odds_after']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    for movement in all_movements:
        writer.writerow(movement)

print(f"Odds movements saved to {csv_file_path}") 
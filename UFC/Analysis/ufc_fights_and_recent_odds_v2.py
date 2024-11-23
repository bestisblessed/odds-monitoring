import os
import json
import csv

folder_path = 'data/' 
date_input = input("Enter the date in the format 'Sat,October 19th': ")

latest_fights = {}
for file in sorted(os.listdir(folder_path), reverse=True):
    if 'ufc_odds_vsin_' in file:
        file_path = os.path.join(folder_path, file)
        try:
            with open(file_path, 'r') as f:
                data = f.read()
                lines = data.splitlines()
                for i, line in enumerate(lines):
                    if date_input in line:
                        fight_and_odds = lines[i:i+10]
                        fight_name = fight_and_odds[0].split(':', 1)[1].strip()
                        if fight_name not in latest_fights:
                            latest_fights[fight_name] = fight_and_odds
        except json.JSONDecodeError:
            continue

formatted_fights = []
for fight_name, fight in latest_fights.items():
    fight_info = {'Matchup': fight_name}
    for line in fight:
        if ":" in line and "Matchup" not in line:
            key, value = line.split(":", 1)
            fight_info[key.strip()] = value.strip()
    formatted_fights.append(fight_info)

output_filename = f"fights_{date_input.replace(',','_').replace(' ','_')}.csv"
if formatted_fights:
    keys = formatted_fights[0].keys()
    with open(output_filename, 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(formatted_fights)

print(f"Fights and odds saved to {output_filename}")


import os
import json

# Function to extract fights for a given day
def extract_fights_for_day(day, folder_path):
    latest_fights = {}
    
    # Loop through all files in the data folder
    for file in sorted(os.listdir(folder_path), reverse=True):  # Sorting by reverse order to get the most recent first
        if 'ufc_odds_vsin_' in file:
            file_path = os.path.join(folder_path, file)
            try:
                with open(file_path, 'r') as f:
                    data = f.read()
                    lines = data.splitlines()
                    for i, line in enumerate(lines):
                        if day in line:
                            # Extract the fight and the next few lines that contain the odds
                            fight_and_odds = lines[i:i+10]
                            fight_name = fight_and_odds[0].split(':', 1)[1].strip()
                            # Only store the first occurrence (the most recent odds) for each fight
                            if fight_name not in latest_fights:
                                latest_fights[fight_name] = fight_and_odds
            except json.JSONDecodeError:
                continue  # Skip files that are not properly formatted as JSON
    
    return latest_fights

# Function to format and display the fights and their odds
def format_fights(fights):
    formatted_fights = []
    for fight_name, fight in fights.items():
        fight_info = {'Matchup': fight_name}
        for line in fight:
            if ":" in line and "Matchup" not in line:
                key, value = line.split(":", 1)
                fight_info[key.strip()] = value.strip()
        formatted_fights.append(fight_info)
    return formatted_fights

# Function to display the extracted fights with odds
def display_fights(fights):
    for fight in fights:
        print(f"Matchup: {fight['Matchup']}")
        for key, value in fight.items():
            if key != "Matchup":
                print(f"{key}: {value}")
        print()

# Path to the folder containing the files
folder_path = 'data/'  # Change this to your actual folder path if different

# Input the desired date
date_input = input("Enter the date in the format 'Sat,October 19th': ")

# Extract, format, and display the fights for the given date
fights = extract_fights_for_day(date_input, folder_path)
formatted_fights = format_fights(fights)
display_fights(formatted_fights)


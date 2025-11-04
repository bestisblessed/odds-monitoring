import os
import re
import csv
import requests
from datetime import datetime

# PUSHOVER CONFIGURATION
PUSHOVER_USER_KEY = os.environ.get('PUSHOVER_USER_KEY')
PUSHOVER_APP_TOKEN = os.environ.get('PUSHOVER_APP_TOKEN')

def send_pushover_notification(message, title="UFC Odds Alert"):
    if not PUSHOVER_USER_KEY or not PUSHOVER_APP_TOKEN:
        print("Pushover credentials not found in environment variables")
        return False
    try:
        response = requests.post("https://api.pushover.net/1/messages.json", data={
            "token": PUSHOVER_APP_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "message": message,
            "title": title,
            "priority": 0
        }, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Pushover notification: {e}")
        return False

def load_files(directory):
    files = [f for f in os.listdir(directory) if re.match(r'ufc_odds_fightoddsio_\d{8}_\d{4}\.csv', f)]
    files.sort(key=lambda x: re.findall(r'(\d{8}_\d{4})', x)[0])
    return files

def detect_odds_movement(odds_before, odds_after):
    movements = []
    for fighter_before, fighter_after in zip(odds_before, odds_after):
        if fighter_before['Fighters'] == fighter_after['Fighters']:
            for sportsbook in fighter_before:
                if sportsbook in ['Fighters', 'Event']:
                    continue
                if (sportsbook in fighter_after and 
                    fighter_before[sportsbook] and fighter_after[sportsbook] and
                    fighter_before[sportsbook] != fighter_after[sportsbook]):
                    movements.append({
                        'event': fighter_before.get('Event', 'Unknown Event'),
                        'fighter': fighter_before['Fighters'],
                        'sportsbook': sportsbook,
                        'odds_before': fighter_before[sportsbook],
                        'odds_after': fighter_after[sportsbook]
                    })
    return movements

def extract_timestamp(filename):
    try:
        timestamp_str = filename.replace('ufc_odds_fightoddsio_', '').replace('.csv', '')
        return datetime.strptime(timestamp_str, '%Y%m%d_%H%M')
    except:
        return None

script_dir = os.path.dirname(os.path.abspath(__file__))
data_directory = os.path.join(script_dir, '../Scraping/data')

if not os.path.exists(data_directory):
    print(f"Data directory not found: {data_directory}")
    exit(1)

files = load_files(data_directory)

if len(files) < 2:
    print("Not enough data files to compare odds movements")
    exit(0)

file1 = files[-2]
file2 = files[-1]

with open(os.path.join(data_directory, file1)) as f1, open(os.path.join(data_directory, file2)) as f2:
    odds_before = list(csv.DictReader(f1))
    odds_after = list(csv.DictReader(f2))

odds_movements = detect_odds_movement(odds_before, odds_after)

if odds_movements:
    timestamp1 = extract_timestamp(file1)
    timestamp2 = extract_timestamp(file2)
    
    time_str = timestamp2.strftime('%I:%M%p').lower().lstrip('0') if timestamp2 else "Unknown"
    
    sportsbooks_of_interest = ['draftkings', 'fanduel', 'betmgm', 'circa-sports', 'caesars']
    
    for movement in odds_movements:
        sportsbook = movement['sportsbook'].lower()
        
        if any(sb in sportsbook for sb in sportsbooks_of_interest):
            fighter = movement['fighter']
            event = movement['event']
            odds_before = movement['odds_before']
            odds_after = movement['odds_after']
            
            message = f"{fighter}\n{event}\n{movement['sportsbook']}: {odds_before} → {odds_after}\n{time_str}"
            
            print(f"Sending notification: {message}")
            send_pushover_notification(message, title="UFC Odds Movement")
    
    print(f"Processed {len(odds_movements)} odds movements")
else:
    print("No odds movements detected")

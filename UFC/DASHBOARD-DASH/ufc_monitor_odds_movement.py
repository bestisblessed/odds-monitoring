import os
import csv
import json
import requests
import re

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_USER_KEY = "uQiRzpo4DXghDmr9QzzfQu27cmVRsG"
PUSHOVER_API_TOKEN = "a3x2jqk1p7n9t5v8w4y6z2c1b3m5d7f9"

seen_fights_file = 'data/seen_fights.txt'
data_directory = '../Scraping/data'

def load_seen_fights():
    if not os.path.exists(seen_fights_file):
        return set()
    with open(seen_fights_file, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_seen_fight(fight_id):
    os.makedirs(os.path.dirname(seen_fights_file), exist_ok=True)
    with open(seen_fights_file, 'a') as f:
        f.write(fight_id + '\n')

def send_pushover_notification(title, message):
    data = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "title": title,
        "message": message,
        "priority": 0
    }
    
    try:
        response = requests.post(PUSHOVER_API_URL, data=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result.get('status') == 1
    except Exception as e:
        print(f"Error sending Pushover notification: {e}")
        return False

def get_latest_fightodds_file():
    if not os.path.exists(data_directory):
        return None
    files = [f for f in os.listdir(data_directory) if re.match(r'ufc_odds_fightoddsio_\d{8}_\d{4}\.csv', f)]
    if not files:
        return None
    files.sort(key=lambda x: re.findall(r'(\d{8}_\d{4})', x)[0], reverse=True)
    return os.path.join(data_directory, files[0]) if files else None

def get_latest_vsin_file():
    if not os.path.exists(data_directory):
        return None
    files = [f for f in os.listdir(data_directory) if re.match(r'ufc_odds_vsin_\d{8}_\d{4}\.json', f)]
    if not files:
        return None
    files.sort(key=lambda x: re.findall(r'(\d{8}_\d{4})', x)[0], reverse=True)
    return os.path.join(data_directory, files[0]) if files else None

def process_fightodds_new_fights(file_path, seen_fights):
    if not file_path or not os.path.exists(file_path):
        return []
    
    new_fights = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fighter = row.get('Fighters', '').strip()
            event = row.get('Event', '').strip()
            if not fighter:
                continue
            
            fight_id = f"fightodds_{event}_{fighter}"
            if fight_id not in seen_fights:
                odds_info = []
                for key, value in row.items():
                    if key not in ['Fighters', 'Event'] and value and str(value).strip():
                        odds_info.append(f"{key}: {str(value).strip()}")
                
                if odds_info:
                    new_fights.append({
                        'fight_id': fight_id,
                        'title': fighter,
                        'event': event,
                        'odds': '\n'.join(odds_info[:10])
                    })
    
    return new_fights

def process_vsin_new_fights(file_path, seen_fights):
    if not file_path or not os.path.exists(file_path):
        return []
    
    new_fights = []
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            return []
        
        for game in data:
            if not isinstance(game, dict):
                continue
            
            keys = list(game.keys())
            if len(keys) < 2:
                continue
            
            matchup_key = keys[1]
            matchup = str(game.get(matchup_key, '')).strip()
            if not matchup:
                continue
            
            fight_id = f"vsin_{matchup}"
            if fight_id not in seen_fights:
                odds_info = []
                for key, value in game.items():
                    if key not in ['Time', matchup_key]:
                        if value and str(value).strip():
                            odds_info.append(f"{key}: {str(value).strip()}")
                
                if odds_info:
                    new_fights.append({
                        'fight_id': fight_id,
                        'title': matchup,
                        'event': '',
                        'odds': '\n'.join(odds_info[:10])
                    })
    except Exception as e:
        print(f"Error processing VSIN file: {e}")
    
    return new_fights

seen_fights = load_seen_fights()
new_fights = []

latest_fightodds = get_latest_fightodds_file()
if latest_fightodds:
    new_fights.extend(process_fightodds_new_fights(latest_fightodds, seen_fights))

latest_vsin = get_latest_vsin_file()
if latest_vsin:
    new_fights.extend(process_vsin_new_fights(latest_vsin, seen_fights))

if not new_fights:
    print("No new fights detected")
    exit(0)

for fight in new_fights:
    title = f"New UFC Fight: {fight['title']}"
    message = f"Opening Odds:\n{fight['odds']}"
    if fight['event']:
        message = f"Event: {fight['event']}\n{message}"
    
    if send_pushover_notification(title, message):
        save_seen_fight(fight['fight_id'])
        print(f"Sent notification for new fight: {fight['title']}")
    else:
        print(f"Failed to send notification for: {fight['title']}")

print(f"Processed {len(new_fights)} new fights")

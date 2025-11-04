import os
import csv
import json
import requests
import re

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_GROUP_KEY = "gvfx5duzqgajxzy3zcb9kepipm78xn"
# PUSHOVER_GROUP_KEY = "ucdzy7t32br76dwht5qtz5mt7fg7n3"
PUSHOVER_API_TOKEN = "a75tq5kqignpk3p8ndgp66bske3bsi"

script_dir = os.path.dirname(os.path.abspath(__file__))
seen_fights_file = os.path.join(script_dir, 'data', 'seen_fights.txt')
data_directory = os.path.join(script_dir, '..', 'Scraping', 'data')
TARGET_PROMOTIONS = ("ufc", "pfl", "lfa", "one")

def normalize_text(text):
    return re.sub(r'\s+', ' ', str(text).strip())

def remove_date_from_event(event_name):
    """Remove date patterns like 'NOVEMBER 21 2' or 'DECEMBER 5 2' from event names."""
    if not event_name:
        return event_name
    # Pattern to match: MONTH_NAME DAY NUMBER (e.g., "NOVEMBER 21 2", "DECEMBER 5 2")
    # This matches month names followed by digits and optional trailing digits
    date_pattern = r'\s+(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d+\s+\d+.*$'
    cleaned = re.sub(date_pattern, '', event_name, flags=re.IGNORECASE)
    return cleaned.strip()

def is_valid_odds(value):
    if not value:
        return False
    value_str = str(value).strip()
    if not value_str or value_str == '-' or value_str == '- -' or value_str.lower() == 'n/a':
        return False
    odds_pattern = re.compile(r'^[+-]?\d+$')
    return bool(odds_pattern.match(value_str))

def load_seen_fights():
    if not os.path.exists(seen_fights_file):
        return set()
    with open(seen_fights_file, 'r') as f:
        seen = set()
        for line in f:
            normalized = normalize_text(line)
            if normalized:
                seen.add(normalized)
        return seen

def save_seen_fight(fight_id):
    os.makedirs(os.path.dirname(seen_fights_file), exist_ok=True)
    normalized_id = normalize_text(fight_id)
    with open(seen_fights_file, 'a') as f:
        f.write(normalized_id + '\n')

def send_pushover_notification(title, message):
    if len(message) > 1024:
        message = message[:1021] + "..."
    if len(title) > 250:
        title = title[:247] + "..."
    
    data = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_GROUP_KEY,
        "title": title,
        "message": message,
        "priority": 0
    }
    
    try:
        response = requests.post(PUSHOVER_API_URL, data=data, timeout=10)
        if response.status_code != 200:
            error_detail = response.text
            print(f"Pushover API error ({response.status_code}): {error_detail}")
            return False
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

def is_target_event(event_name):
    if not event_name:
        return False
    normalized = normalize_text(event_name).lower()
    return any(keyword in normalized for keyword in TARGET_PROMOTIONS)


def process_fightodds_new_fights(file_path, seen_fights):
    if not file_path or not os.path.exists(file_path):
        return []
    
    new_fights = []
    rows = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Group fighters by event
    events = {}
    for i, row in enumerate(rows):
        fighter = normalize_text(row.get('Fighters', ''))
        event = normalize_text(row.get('Event', ''))
        if not fighter or not event or not is_target_event(event):
            continue
        if event not in events:
            events[event] = []
        events[event].append((i, fighter, row))
    
    # Process each event, pairing consecutive fighters
    for event, fighters_list in events.items():
        for idx, (i, fighter, row) in enumerate(fighters_list):
            opponent = None
            # Pair consecutive fighters within the same event
            # If even index, opponent is next fighter (odd index)
            # If odd index, opponent is previous fighter (even index)
            if idx % 2 == 0 and idx + 1 < len(fighters_list):
                opponent = fighters_list[idx + 1][1]
            elif idx % 2 == 1 and idx > 0:
                opponent = fighters_list[idx - 1][1]
            
            fight_id = f"fightodds_{event}_{fighter}"
            if fight_id not in seen_fights:
                first_odds = None
                first_book = None
                for key, value in row.items():
                    if key not in ['Fighters', 'Event'] and is_valid_odds(value):
                        if first_odds is None:
                            first_odds = str(value).strip()
                            first_book = key
                            break
                
                if first_odds:
                    new_fights.append({
                        'fight_id': fight_id,
                        'title': fighter,
                        'opponent': opponent,
                        'event': event,
                        'odds': f"{first_book}: {first_odds}"
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
            matchup = game.get(matchup_key, '')
            if not matchup:
                continue
            
            fighters = [normalize_text(f.strip()) for f in str(matchup).split('\n') if f.strip()]
            if len(fighters) < 1:
                continue
            
            fighter = fighters[0]
            opponent = fighters[1] if len(fighters) > 1 else None
            
            fight_id = f"vsin_{normalize_text(matchup)}"
            if fight_id not in seen_fights:
                first_odds = None
                first_book = None
                for key, value in game.items():
                    if key not in ['Time', matchup_key]:
                        if is_valid_odds(value):
                            if first_odds is None:
                                odds_values = str(value).strip().split('\n')
                                if odds_values:
                                    first_odds = odds_values[0].strip()
                                    first_book = key
                                    break
                
                if first_odds:
                    new_fights.append({
                        'fight_id': fight_id,
                        'title': fighter,
                        'opponent': opponent,
                        'event': '',
                        'odds': f"{first_book}: {first_odds}"
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
    title = "🚨 OPENING ODDS 🚨"
    
    parts = [""]
    if fight.get('event'):
        event_name = remove_date_from_event(fight['event'])
        parts.append(f"📅 {event_name}")
    parts.append(f"🥊 {fight['title']}")
    if fight.get('opponent'):
        parts.append(f"   vs. {fight['opponent']}")
    parts.append(f"💵  {fight['odds']}")
    message = "\n".join(parts)
    
    if send_pushover_notification(title, message):
        save_seen_fight(fight['fight_id'])
        print(f"Sent notification for: {fight['title']} - {fight['odds']}")
    else:
        print(f"Failed to send notification for: {fight['title']}")

print(f"Processed {len(new_fights)} new fights")


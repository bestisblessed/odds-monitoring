import os
import csv
import requests

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_USER_KEY = os.environ.get('PUSHOVER_USER_KEY')
PUSHOVER_API_TOKEN = os.environ.get('PUSHOVER_API_TOKEN')

csv_file_path_vsin = 'data/ufc_odds_movements.csv'
csv_file_path_fightodds = 'data/ufc_odds_movements_fightoddsio.csv'
sent_notifications_file = 'data/sent_notifications.txt'

def load_sent_notifications():
    if not os.path.exists(sent_notifications_file):
        return set()
    with open(sent_notifications_file, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_notification(notification_id):
    os.makedirs(os.path.dirname(sent_notifications_file), exist_ok=True)
    with open(sent_notifications_file, 'a') as f:
        f.write(notification_id + '\n')

def send_pushover_notification(title, message):
    if not PUSHOVER_USER_KEY or not PUSHOVER_API_TOKEN:
        print("ERROR: PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN environment variables must be set")
        return False
    
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

def create_notification_id(row, source):
    if source == 'vsin':
        return f"{row['file1']}_{row['file2']}_{row['matchup']}_{row['sportsbook']}_{row['odds_before']}_{row['odds_after']}"
    else:
        return f"{row['file1']}_{row['file2']}_{row['fighter']}_{row['sportsbook']}_{row['odds_before']}_{row['odds_after']}"

def process_csv(csv_path, source):
    if not os.path.exists(csv_path):
        return []
    
    sent_notifications = load_sent_notifications()
    new_movements = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            notification_id = create_notification_id(row, source)
            if notification_id not in sent_notifications:
                new_movements.append((notification_id, row, source))
    
    return new_movements

all_new_movements = []
all_new_movements.extend(process_csv(csv_file_path_vsin, 'vsin'))
all_new_movements.extend(process_csv(csv_file_path_fightodds, 'fightodds'))

if not all_new_movements:
    print("No new odds movements detected")
    exit(0)

for notification_id, row, source in all_new_movements:
    if source == 'vsin':
        title = f"UFC Odds Movement: {row['matchup']}"
        message = f"{row['sportsbook']}: {row['odds_before']} → {row['odds_after']}\nTime: {row.get('game_time', 'N/A')}"
    else:
        title = f"UFC Odds Movement: {row['fighter']}"
        message = f"{row['sportsbook']}: {row['odds_before']} → {row['odds_after']}"
    
    if send_pushover_notification(title, message):
        save_notification(notification_id)
        print(f"Sent notification for {title}")
    else:
        print(f"Failed to send notification for {title}")

print(f"Processed {len(all_new_movements)} new odds movements")

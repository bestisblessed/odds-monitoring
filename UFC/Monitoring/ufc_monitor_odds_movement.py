import os
import csv
import requests
import re
import time

time.sleep(30)

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_GROUP_KEY = "gvfx5duzqgajxzy3zcb9kepipm78xn"
# PUSHOVER_GROUP_KEY = "ucdzy7t32br76dwht5qtz5mt7fg7n3"
PUSHOVER_API_TOKEN = "a75tq5kqignpk3p8ndgp66bske3bsi"

script_dir = os.path.dirname(os.path.abspath(__file__))
seen_fights_file = os.path.join(script_dir, 'data', 'seen_fights.txt')
seen_totals_file = os.path.join(script_dir, 'data', 'seen_totals.txt')
data_directory = os.path.join(script_dir, '..', 'Scraping', 'data')
TARGET_PROMOTIONS = ("ufc", "pfl", "lfa", "one", "oktagon", "cwfc", "rizin", "bcf", "brave", "uaew", "ksw")

def normalize_text(text):
    return re.sub(r'\s+', ' ', str(text).strip())

def clean_fighter_name(fighter_name):
    """Remove leading numbers and special characters from fighter names."""
    if not fighter_name:
        return fighter_name
    # Remove leading numbers, dots, dashes, and whitespace
    cleaned = re.sub(r'^[\d.\-\s]+', '', str(fighter_name))
    return normalize_text(cleaned)

def remove_date_from_event(event_name):
    """Remove date patterns like 'NOVEMBER 21 2' or 'DECEMBER 5 2' from event names."""
    if not event_name:
        return event_name
    # Pattern to match: MONTH_NAME DAY NUMBER (e.g., "NOVEMBER 21 2", "DECEMBER 5 2")
    # This matches month names followed by digits and optional trailing digits
    date_pattern = r'\s+(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d+\s+\d+.*$'
    cleaned = re.sub(date_pattern, '', event_name, flags=re.IGNORECASE)
    # Remove trailing standalone month names (e.g., "UFC 322 ... NOVEMBER")
    month_only_pattern = r'\s+(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)$'
    cleaned = re.sub(month_only_pattern, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def extract_date_from_event(event_name):
    """Extract date pattern like 'NOVEMBER 7 13' from event names."""
    if not event_name:
        return None
    # Pattern to match: MONTH_NAME DAY NUMBER (e.g., "NOVEMBER 7 13", "DECEMBER 5 2")
    date_pattern = r'((?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d+\s+\d+)'
    match = re.search(date_pattern, event_name, re.IGNORECASE)
    if match:
        return normalize_text(match.group(1))
    return None

def create_fight_id(event, fighter):
    """Create a fight ID using fighter name + a normalized YYYYMMDD date extracted from event.
    Pads month/day to two digits (YYYYMMDD). Falls back to an event-token if date cannot be parsed.
    """
    cleaned_fighter = clean_fighter_name(fighter)
    date_text = extract_date_from_event(event)
    # prefer MMDD token from event (ignore year)
    mmdd = normalize_date_text_to_MMDD(date_text) if date_text else None
    if mmdd:
        return f"fight_{mmdd}_{slugify_fighter_for_id(cleaned_fighter)}"
    # fallback: create an event token safe for IDs
    event_token = normalize_text(event) if event else 'unknown'
    event_token = re.sub(r'\s+', '_', event_token)
    event_token = re.sub(r'[^a-zA-Z0-9_]', '', event_token).lower()
    return f"fight_{event_token}_{slugify_fighter_for_id(cleaned_fighter)}"


def slugify_fighter_for_id(fighter_name):
    """Return a filesystem/ID-safe slug for a fighter name."""
    if not fighter_name:
        return ''
    cleaned = clean_fighter_name(fighter_name)
    # replace spaces with underscores and remove characters that could vary
    slug = re.sub(r"[^a-zA-Z0-9_]+", '', cleaned.replace(' ', '_'))
    return slug.lower()


def date_from_filename(file_path):
    """Extract YYYYMMDD from filenames like ..._YYYYMMDD_HHMM.ext"""
    if not file_path:
        return None
    base = os.path.basename(file_path)
    m = re.search(r'(\d{8})_\d{4}', base)
    if m:
        return m.group(1)
    # fallback: look for any 8-digit sequence
    m2 = re.search(r'(\d{8})', base)
    if m2:
        return m2.group(1)
    return None


def normalize_date_text_to_YYYYMMDD(date_text, fallback_year=None):
    """Try to convert date text like 'NOVEMBER 7 13' or 'NOVEMBER 7' to YYYYMMDD.
    If year is missing, return None so caller can fallback to filename date.
    """
    if not date_text:
        return None
    # attempt to parse: MonthName Day YearOrTwoDigit
    m = re.search(r'(?i)(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{1,2})(?:\s+(\d{2,4}))?', date_text)
    if not m:
        return None
    month_name = m.group(1)
    day = int(m.group(2))
    year_part = m.group(3)
    month_num = {
        'JANUARY':1,'FEBRUARY':2,'MARCH':3,'APRIL':4,'MAY':5,'JUNE':6,
        'JULY':7,'AUGUST':8,'SEPTEMBER':9,'OCTOBER':10,'NOVEMBER':11,'DECEMBER':12
    }.get(month_name.upper())
    if not month_num:
        return None
    if year_part:
        y = int(year_part)
        if y < 100:
            # two-digit year -> assume 2000s
            y += 2000
    else:
        # no year information; let caller fallback to filename
        return None
    return f"{y:04d}{month_num:02d}{day:02d}"


def normalize_date_text_to_MMDD(date_text):
    """Extract month/day from event text and return zero-padded MMDD (e.g. '1107')."""
    if not date_text:
        return None
    m = re.search(r'(?i)(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{1,2})', date_text)
    if not m:
        return None
    month_name = m.group(1)
    day = int(m.group(2))
    month_num = {
        'JANUARY':1,'FEBRUARY':2,'MARCH':3,'APRIL':4,'MAY':5,'JUNE':6,
        'JULY':7,'AUGUST':8,'SEPTEMBER':9,'OCTOBER':10,'NOVEMBER':11,'DECEMBER':12
    }.get(month_name.upper())
    if not month_num:
        return None
    return f"{month_num:02d}{day:02d}"


def canonical_fight_id(file_path, event, fighter, source='fightodds', matchup=None):
    """Return canonical ID: fight_{YYYYMMDD}_{fighter_slug}.
    Prefer date from event; if not present, fall back to date from filename.
    """
    fighter_slug = slugify_fighter_for_id(fighter)
    # try extract month/day from event and prefer that (MMDD)
    date_text = extract_date_from_event(event) if event else None
    date_token = None
    if date_text:
        date_token = normalize_date_text_to_MMDD(date_text)
    # if no month/day from event, fall back to filename full date YYYYMMDD
    if not date_token:
        date_token = date_from_filename(file_path)
    if not date_token:
        date_token = 'unknown'
    return f"fight_{date_token}_{fighter_slug}"

def canonical_total_group_id(file_path, event, fighter1, fighter2):
    date_text = extract_date_from_event(event) if event else None
    date_token = normalize_date_text_to_MMDD(date_text) if date_text else None
    if not date_token:
        date_token = date_from_filename(file_path)
    if not date_token:
        date_token = 'unknown'
    fighter_tokens = '_'.join(filter(None, [slugify_fighter_for_id(fighter1), slugify_fighter_for_id(fighter2)]))
    if not fighter_tokens:
        fighter_tokens = 'unknown'
    return f"total_{date_token}_{fighter_tokens}"

def canonical_total_id(file_path, event, totals_type, fighter1, fighter2):
    group_token = canonical_total_group_id(file_path, event, fighter1, fighter2)
    totals_token = normalize_text(totals_type).lower().replace(' ', '_')
    totals_token = re.sub(r'[^a-z0-9_]', '', totals_token)
    if not totals_token:
        totals_token = 'total'
    return f"{group_token}_{totals_token}"

def canonical_moneyline_group_id(file_path, event, fighter1, fighter2):
    date_text = extract_date_from_event(event) if event else None
    date_token = normalize_date_text_to_MMDD(date_text) if date_text else None
    if not date_token:
        date_token = date_from_filename(file_path)
    if not date_token:
        date_token = 'unknown'
    fighter_slugs = sorted(filter(None, [
        slugify_fighter_for_id(fighter1),
        slugify_fighter_for_id(fighter2)
    ]))
    if fighter_slugs:
        fighter_token = '_'.join(fighter_slugs)
    else:
        fighter_token = 'unknown'
    event_token = normalize_text(event) if event else ''
    event_token = re.sub(r'\s+', '_', event_token)
    event_token = re.sub(r'[^a-zA-Z0-9_]', '', event_token).lower()
    return f"fightgroup_{date_token}_{fighter_token}_{event_token}"

def is_valid_odds(value):
    if not value:
        return False
    value_str = str(value).strip()
    if not value_str or value_str == '-' or value_str == '- -' or value_str.lower() == 'n/a':
        return False
    odds_pattern = re.compile(r'^[+-]?\d+$')
    return bool(odds_pattern.match(value_str))

def clean_fight_id_from_file(fight_id):
    """Normalize legacy fight IDs from file into a simplified token.
    This attempts to handle previous prefixes like 'fightodds_' and 'vsin_'
    by converting them to the canonical 'fight_{date}_{fighter_slug}' style when possible.
    """
    if not fight_id:
        return ''
    s = normalize_text(fight_id)
    # replace known prefixes
    s = re.sub(r'^(fightodds_|vsin_)', 'fight_', s, flags=re.IGNORECASE)
    # replace spaces with underscores and remove excessive chars
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'[^a-zA-Z0-9_]', '', s)
    return s.lower()

def load_seen_fights():
    """Load seen fights from the data file, cleaning fighter names from existing entries."""
    if not os.path.exists(seen_fights_file):
        return set()
    seen = set()
    with open(seen_fights_file, 'r') as f:
        for line in f:
            normalized = normalize_text(line)
            if normalized:
                cleaned = clean_fight_id_from_file(normalized)
                if cleaned:
                    seen.add(cleaned)
    return seen

def load_seen_totals():
    if not os.path.exists(seen_totals_file):
        return set()
    seen = set()
    with open(seen_totals_file, 'r') as f:
        for line in f:
            normalized = normalize_text(line)
            if normalized:
                cleaned = clean_fight_id_from_file(normalized)
                if cleaned:
                    seen.add(cleaned)
    return seen

def save_seen_fight(fight_id):
    os.makedirs(os.path.dirname(seen_fights_file), exist_ok=True)
    # Assume fight_id provided by processors is already canonical; normalize for safety
    normalized_id = normalize_text(fight_id)
    normalized_id = clean_fight_id_from_file(normalized_id)
    with open(seen_fights_file, 'a') as f:
        f.write(normalized_id + '\n')

def save_seen_total(total_id):
    os.makedirs(os.path.dirname(seen_totals_file), exist_ok=True)
    normalized_id = normalize_text(total_id)
    normalized_id = clean_fight_id_from_file(normalized_id)
    with open(seen_totals_file, 'a') as f:
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

def get_latest_totals_file():
    if not os.path.exists(data_directory):
        return None
    files = [f for f in os.listdir(data_directory) if re.match(r'ufc_totals_fightoddsio_\d{8}_\d{4}\.csv', f)]
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
    
    rows = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    grouped_fights = {}
    for index_order, row in enumerate(rows):
        fighter_raw = row.get('Fighters', '')
        fighter = clean_fighter_name(fighter_raw)
        event = normalize_text(row.get('Event', ''))
        if not fighter or not event or not is_target_event(event):
            continue

        fighter1 = clean_fighter_name(row.get('Fighter1', ''))
        fighter2 = clean_fighter_name(row.get('Fighter2', ''))
        pair_names = []
        for name in [fighter1, fighter2]:
            if name and name not in pair_names:
                pair_names.append(name)
        if fighter and fighter not in pair_names:
            pair_names.append(fighter)
        unique_names = []
        for name in pair_names:
            if name and name not in unique_names:
                unique_names.append(name)
        if len(unique_names) < 2:
            continue
        pair_sorted = sorted(unique_names)[:2]

        fight_id = canonical_fight_id(file_path, event, fighter, source='fightodds')
        normalized_fight_id = normalize_text(fight_id)

        first_odds = None
        first_book = None
        for key, value in row.items():
            if key in ['Fighters', 'Fighter1', 'Fighter2', 'Event']:
                continue
            if is_valid_odds(value):
                first_odds = str(value).strip()
                first_book = key
                break
        if not first_odds:
            continue

        group_id_raw = canonical_moneyline_group_id(file_path, event, pair_sorted[0], pair_sorted[1])
        group_id = clean_fight_id_from_file(normalize_text(group_id_raw))
        if group_id not in grouped_fights:
            grouped_fights[group_id] = {
                'event': event,
                'pair': pair_sorted,
                'fighters': {}
            }
        group_entry = grouped_fights[group_id]
        fighter_bucket = group_entry['fighters']
        if fighter not in fighter_bucket or index_order < fighter_bucket[fighter]['order']:
            fighter_bucket[fighter] = {
                'name': fighter,
                'book': first_book,
                'odds': first_odds,
                'fight_id': normalized_fight_id,
                'order': index_order
            }

    new_fights = []
    for group in grouped_fights.values():
        fighters_map = group['fighters']
        if not fighters_map:
            continue
        fighters = sorted(fighters_map.values(), key=lambda e: e['order'])
        if len(fighters) < 2:
            continue
        new_ids = [fighter['fight_id'] for fighter in fighters if fighter['fight_id'] not in seen_fights]
        if not new_ids:
            continue
        new_fights.append({
            'event': group['event'],
            'fighters': [{'name': fighter['name'], 'book': fighter['book'], 'odds': fighter['odds']} for fighter in fighters],
            'fight_ids': new_ids
        })
    
    return new_fights

# VSIN processing removed — this script only processes fightodds files

def clean_seen_fights_file():
    """Clean all entries in seen_fights.txt file to remove leading numbers from fighter names."""
    if not os.path.exists(seen_fights_file):
        return
    # Read and clean all entries
    cleaned_entries = set()
    with open(seen_fights_file, 'r') as f:
        for line in f:
            normalized = normalize_text(line)
            if normalized:
                cleaned = clean_fight_id_from_file(normalized)
                cleaned_entries.add(cleaned)
    # Write back cleaned entries
    os.makedirs(os.path.dirname(seen_fights_file), exist_ok=True)
    with open(seen_fights_file, 'w') as f:
        for entry in sorted(cleaned_entries):
            f.write(entry + '\n')

# Clean the file on startup to ensure all existing entries are cleaned
clean_seen_fights_file()

def clean_seen_totals_file():
    if not os.path.exists(seen_totals_file):
        return
    cleaned_entries = set()
    with open(seen_totals_file, 'r') as f:
        for line in f:
            normalized = normalize_text(line)
            if normalized:
                cleaned = clean_fight_id_from_file(normalized)
                cleaned_entries.add(cleaned)
    os.makedirs(os.path.dirname(seen_totals_file), exist_ok=True)
    with open(seen_totals_file, 'w') as f:
        for entry in sorted(cleaned_entries):
            f.write(entry + '\n')

clean_seen_totals_file()

def process_fightodds_new_totals(file_path, seen_totals):
    if not file_path or not os.path.exists(file_path):
        return []
    groups = {}
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            totals_type = normalize_text(row.get('Totals_Type', ''))
            event = normalize_text(row.get('Event', ''))
            if not totals_type or not event or not is_target_event(event):
                continue
            fighter1 = clean_fighter_name(row.get('Fighter1', ''))
            fighter2 = clean_fighter_name(row.get('Fighter2', ''))
            group_token = canonical_total_group_id(file_path, event, fighter1, fighter2)
            normalized_group_id = clean_fight_id_from_file(normalize_text(group_token))
            first_odds = None
            first_book = None
            for key, value in row.items():
                if key in ['Fighter1', 'Fighter2', 'Totals_Type', 'Event']:
                    continue
                if is_valid_odds(value):
                    first_odds = str(value).strip()
                    first_book = key
                    break
            if first_odds:
                total_id = canonical_total_id(file_path, event, totals_type, fighter1, fighter2)
                normalized_total_id = clean_fight_id_from_file(normalize_text(total_id))
                if normalized_total_id in seen_totals:
                    continue
                matchup = None
                if fighter1 and fighter2:
                    matchup = f"{fighter1} vs {fighter2}"
                elif fighter1 or fighter2:
                    matchup = fighter1 or fighter2
                if normalized_group_id not in groups:
                    groups[normalized_group_id] = {
                        'group_id': normalized_group_id,
                        'event': event,
                        'matchup': matchup,
                        'totals': [],
                        'total_ids': []
                    }
                group_entry = groups[normalized_group_id]
                if not group_entry.get('matchup') and matchup:
                    group_entry['matchup'] = matchup
                group_entry['totals'].append({
                    'totals_type': totals_type,
                    'odds': f"{first_book}: {first_odds}",
                    'total_id': normalized_total_id
                })
                group_entry['total_ids'].append(normalized_total_id)
    # Filter out groups with no totals (in case all were seen)
    return [group for group in groups.values() if group['totals']]

seen_fights = load_seen_fights()
seen_totals = load_seen_totals()
new_fights = []
new_totals = []

latest_fightodds = get_latest_fightodds_file()
if latest_fightodds:
    new_fights.extend(process_fightodds_new_fights(latest_fightodds, seen_fights))

latest_totals = get_latest_totals_file()
if latest_totals:
    new_totals.extend(process_fightodds_new_totals(latest_totals, seen_totals))

if not new_fights and not new_totals:
    print("No new odds detected")
    exit(0)

for fight in new_fights:
    title = "🚨 OPENING ODDS 🚨"

    parts = [""]
    if fight.get('event'):
        event_name = remove_date_from_event(fight['event'])
        parts.append(f"📅  {event_name}")
    for fighter in fight['fighters']:
        parts.append(f"💵  {fighter['name']} - {fighter['book']}: {fighter['odds']}")
    message = "\n".join(parts)

    if send_pushover_notification(title, message):
        for fight_id in fight['fight_ids']:
            save_seen_fight(fight_id)
            seen_fights.add(fight_id)
        fighter_names = ", ".join(fighter['name'] for fighter in fight['fighters'])
        print(f"Sent notification for fighters: {fighter_names}")
    else:
        fighter_names = ", ".join(fighter['name'] for fighter in fight['fighters'])
        print(f"Failed to send notification for fighters: {fighter_names}")

for total_group in new_totals:
    title = "🚨 TOTALS OPENING ODDS 🚨"
    
    parts = [""]
    if total_group.get('event'):
        event_name = remove_date_from_event(total_group['event'])
        parts.append(f"📅  {event_name}")
    if total_group.get('matchup'):
        parts.append(f"🥊  {total_group['matchup']}")
    for totals_entry in total_group['totals']:
        parts.append(f"📈  {totals_entry['totals_type']} — {totals_entry['odds']}")
    message = "\n".join(parts)
    
    if send_pushover_notification(title, message):
        for total_id in total_group['total_ids']:
            save_seen_total(total_id)
        print(f"Sent totals notification for: {total_group.get('matchup', total_group.get('event', 'Totals'))}")
    else:
        print("Failed to send totals notification for totals group")

if new_fights:
    print(f"Processed {len(new_fights)} new fights")
if new_totals:
    print(f"Processed {len(new_totals)} new totals")


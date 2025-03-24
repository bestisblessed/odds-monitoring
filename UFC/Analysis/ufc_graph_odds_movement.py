import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os
import re
from matplotlib.backends.backend_pdf import PdfPages

# Calculate the next Saturday (same as in ufc_fights_and_recent_odds_v2.py)
today = datetime.now()
days_ahead = (5 - today.weekday() + 7) % 7
next_saturday = today + timedelta(days=days_ahead)
day = next_saturday.day
suffix = 'th' if 11 <= day <= 13 else {1:'st', 2:'nd', 3:'rd'}.get(day % 10, 'th')
default_date = next_saturday.strftime(f"%a,%B {day}{suffix}")

# Automatically use default date without input
fight_date = default_date  # The date to filter by

# Load the odds movements data
csv_file_path = 'data/ufc_odds_movements.csv'
df = pd.read_csv(csv_file_path)

# Filter to only include matchups for the specified date
df_filtered = df[df['game_date'].str.contains(fight_date, na=False)]

# Extract timestamp from filenames for x-axis
def extract_timestamp(filename):
    match = re.search(r'ufc_odds_vsin_(\d{8})_(\d{4})', filename)
    if match:
        date_str, time_str = match.groups()
        return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M")
    return None

# Add timestamp column
df_filtered['timestamp'] = df_filtered['file2'].apply(extract_timestamp)

# Function to extract both fighters' odds
def extract_fighter_odds(odds_str):
    if pd.isna(odds_str) or '|' not in odds_str:
        return None, None
    
    parts = odds_str.split('|')
    if len(parts) < 2:
        return None, None
    
    fighter1_odds = parts[0].strip()
    fighter2_odds = parts[1].strip()
    
    # Convert to integers if possible
    try:
        if fighter1_odds and fighter1_odds != '-':
            fighter1_odds = int(fighter1_odds.replace('+', '').replace('-', '')) * (-1 if '-' in fighter1_odds else 1)
        else:
            fighter1_odds = None
    except:
        fighter1_odds = None
        
    try:
        if fighter2_odds and fighter2_odds != '-':
            fighter2_odds = int(fighter2_odds.replace('+', '').replace('-', '')) * (-1 if '-' in fighter2_odds else 1)
        else:
            fighter2_odds = None
    except:
        fighter2_odds = None
        
    return fighter1_odds, fighter2_odds

# Create a directory to save individual plots (optional)
os.makedirs('odds_graphs', exist_ok=True)

# Create a PDF to save all plots
pdf_path = f'odds_graphs/UFC_Odds_Movement_{fight_date.replace(",", "_").replace(" ", "_")}.pdf'
pdf = PdfPages(pdf_path)

# Get unique matchups from the filtered data
matchups = df_filtered['matchup'].unique()

# Track which fights have data
processed_matchups = []

# Process each matchup from the filtered data
for matchup in matchups:
    # Get data for this matchup
    matchup_data = df_filtered[df_filtered['matchup'] == matchup].copy()
    
    # Skip if not enough data
    if len(matchup_data) < 2:
        continue
    
    # Record that we're processing this matchup
    processed_matchups.append(matchup)
    
    # Sort by timestamp
    matchup_data = matchup_data.sort_values('timestamp')
    
    # Extract fighter names from matchup
    fighters = matchup.split(' vs ')
    if len(fighters) != 2:
        continue
    
    fighter1 = fighters[0].strip()
    fighter2 = fighters[1].strip()
    
    # Create a figure for this matchup
    fig = plt.figure(figsize=(12, 8))
    
    # Create data structures to track odds over time
    time_data = {}
    
    # Process each row to extract odds data
    for _, row in matchup_data.iterrows():
        timestamp = row['timestamp']
        
        # Initialize time data if needed
        if timestamp not in time_data:
            time_data[timestamp] = {
                'fighter1_odds': [],
                'fighter2_odds': []
            }
        
        # Extract odds for both before and after
        before_f1, before_f2 = extract_fighter_odds(row['odds_before'])
        after_f1, after_f2 = extract_fighter_odds(row['odds_after'])
        
        # Add valid odds to respective lists
        if before_f1 is not None:
            time_data[timestamp]['fighter1_odds'].append(before_f1)
        if before_f2 is not None:
            time_data[timestamp]['fighter2_odds'].append(before_f2)
        if after_f1 is not None:
            time_data[timestamp]['fighter1_odds'].append(after_f1)
        if after_f2 is not None:
            time_data[timestamp]['fighter2_odds'].append(after_f2)
    
    # Prepare data for plotting
    sorted_timestamps = sorted(time_data.keys())
    
    f1_odds = []  # Will contain worst odds if negative, best if positive
    f2_odds = []  # Will contain worst odds if negative, best if positive
    
    # Determine if fighters are generally favorites or underdogs across all timestamps
    all_f1_odds = []
    all_f2_odds = []
    
    for timestamp in sorted_timestamps:
        all_f1_odds.extend(time_data[timestamp]['fighter1_odds'])
        all_f2_odds.extend(time_data[timestamp]['fighter2_odds'])
    
    # Calculate if each fighter is predominantly a favorite or underdog
    f1_is_favorite = sum(1 for x in all_f1_odds if x < 0) > sum(1 for x in all_f1_odds if x > 0)
    f2_is_favorite = sum(1 for x in all_f2_odds if x < 0) > sum(1 for x in all_f2_odds if x > 0)
    
    # Extract the relevant odds based on favorite/underdog status
    for timestamp in sorted_timestamps:
        # Fighter 1 odds
        if time_data[timestamp]['fighter1_odds']:
            odds_list = time_data[timestamp]['fighter1_odds']
            if f1_is_favorite:
                # If favorite, get worst odds (most negative)
                f1_odds.append(min(odds_list) if odds_list else None)
            else:
                # If underdog, get best odds (most positive)
                f1_odds.append(max(odds_list) if odds_list else None)
        else:
            f1_odds.append(None)
        
        # Fighter 2 odds
        if time_data[timestamp]['fighter2_odds']:
            odds_list = time_data[timestamp]['fighter2_odds']
            if f2_is_favorite:
                # If favorite, get worst odds (most negative)
                f2_odds.append(min(odds_list) if odds_list else None)
            else:
                # If underdog, get best odds (most positive)
                f2_odds.append(max(odds_list) if odds_list else None)
        else:
            f2_odds.append(None)
    
    # Remove None values for plotting (keep track of their indices)
    valid_indices = []
    for i in range(len(sorted_timestamps)):
        if f1_odds[i] is not None and f2_odds[i] is not None:
            valid_indices.append(i)
    
    valid_timestamps = [sorted_timestamps[i] for i in valid_indices]
    valid_f1_odds = [f1_odds[i] for i in valid_indices]
    valid_f2_odds = [f2_odds[i] for i in valid_indices]
    
    # Only create plot if we have valid data
    if valid_timestamps:
        # Plot fighter 1 odds (worst if favorite, best if underdog)
        f1_label = f"{fighter1} - Odds"
        plt.plot(valid_timestamps, valid_f1_odds, linestyle='-', color='blue', marker='o',
                 label=f1_label, markevery=[0, -1])  # Mark first and last points
        
        # Plot fighter 2 odds (worst if favorite, best if underdog)
        f2_label = f"{fighter2} - Odds"
        plt.plot(valid_timestamps, valid_f2_odds, linestyle='-', color='red', marker='o',
                 label=f2_label, markevery=[0, -1])  # Mark first and last points
        
        # Format the plot
        plt.title(f"Odds Movement for {matchup}", fontsize=16)
        plt.xlabel("Date/Time", fontsize=12)
        plt.ylabel("American Odds", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Add a horizontal line at 0
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # Find min and max odds values
        min_odds = min(min(valid_f1_odds), min(valid_f2_odds))
        max_odds = max(max(valid_f1_odds), max(valid_f2_odds))
        
        # Set y-axis limits in increments of 100, expanding to fit all data
        if min_odds < -100:
            # Round down to nearest 100
            y_min = -100 * ((-min_odds // 100) + 1)
        else:
            y_min = -100
        
        if max_odds > 100:
            # Round up to nearest 100
            y_max = 100 * ((max_odds // 100) + 1)
        else:
            y_max = 100
        
        # Make sure the axis is always centered around 0
        if abs(y_min) > y_max:
            y_max = abs(y_min)
        elif y_max > abs(y_min):
            y_min = -y_max
        
        plt.ylim(y_min, y_max)
        
        # Set y-ticks to be in increments of 100
        plt.yticks(range(int(y_min), int(y_max) + 1, 100))
        
        # Format the x-axis to show dates nicely
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.gcf().autofmt_xdate()
        
        # Add legend with smaller font in the middle right
        plt.legend(loc='center right', fontsize=10, bbox_to_anchor=(1.15, 0.5))
        
        # Adjust layout to prevent legend cutoff
        plt.tight_layout()
        
        # Save to PDF
        pdf.savefig(fig, bbox_inches='tight')
        
        # Also save as individual PNG (optional)
        safe_matchup = matchup.replace('/', '_').replace('\\', '_').replace(' ', '_')
        plt.savefig(f"odds_graphs/{safe_matchup}_odds_movement.png", dpi=300, bbox_inches='tight')
    
    plt.close(fig)

# Close the PDF
pdf.close()

# Print summary
print(f"Processed and saved odds movement graphs for {len(processed_matchups)} fights on {fight_date}.")
print(f"All graphs saved to PDF: {pdf_path}")
if processed_matchups:
    print("Processed fights:")
    for i, matchup in enumerate(processed_matchups, 1):
        print(f"{i}. {matchup}")
else:
    print(f"No fights with odds movement data were found for {fight_date}.")
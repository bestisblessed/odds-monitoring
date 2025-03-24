import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt
import re

# Load data
df = pd.read_csv("data/ufc_odds_movements.csv")  # Adjust path if needed

# Step 1: Chronologically ordered event dates
def parse_game_date(date_str):
    month_day = re.sub(r'(st|nd|rd|th)', '', date_str.split(',')[1].strip())
    return dt.datetime.strptime(f"2025 {month_day}", "%Y %B %d")

dates_raw = df['game_date'].unique().tolist()
dates_parsed = [(d, parse_game_date(d)) for d in dates_raw]
dates_sorted = sorted(dates_parsed, key=lambda x: x[1])
dates = [d[0] for d in dates_sorted]

print("\n📆 Available Event Dates:")
for idx, date in enumerate(dates, start=1):
    print(f"{idx}. {date}")

while True:
    try:
        date_choice = int(input("\nSelect an event date by number: "))
        if 1 <= date_choice <= len(dates):
            selected_date = dates[date_choice - 1]
            break
    except ValueError:
        pass
    print("Please enter a valid number.")

# Step 2: Matchup selection
df_date = df[df['game_date'] == selected_date]
matchups = sorted(df_date['matchup'].unique().tolist())

print(f"\n🥊 Matchups on {selected_date}:")
for idx, matchup in enumerate(matchups, start=1):
    print(f"{idx}. {matchup}")

while True:
    try:
        matchup_choice = int(input("\nSelect a matchup by number: "))
        if 1 <= matchup_choice <= len(matchups):
            selected_matchup = matchups[matchup_choice - 1]
            break
    except ValueError:
        pass
    print("Please enter a valid number.")

# Step 3: Sportsbook selection
sportsbooks = sorted(df_date[df_date['matchup'] == selected_matchup]['sportsbook'].unique().tolist())
print("\n📈 Available Sportsbooks:")
for idx, book in enumerate(sportsbooks, start=1):
    print(f"{idx}. {book}")

while True:
    try:
        book_choice = int(input("\nSelect a sportsbook by number (default is Circa): ") or sportsbooks.index("Circa") + 1)
        if 1 <= book_choice <= len(sportsbooks):
            sportsbook_input = sportsbooks[book_choice - 1]
            break
    except (ValueError, IndexError):
        print("Please enter a valid number.")

# Step 4: Filter and parse odds movement
df_filtered = df_date[(df_date['matchup'] == selected_matchup) & (df_date['sportsbook'] == sportsbook_input)].copy()

def parse_moneyline(odds_str):
    try:
        left, right = odds_str.split('|')
        return float(left.strip().replace('+', '')), float(right.strip().replace('+', ''))
    except:
        return None, None

df_filtered[['fighter1_before', 'fighter2_before']] = df_filtered['odds_before'].apply(lambda x: pd.Series(parse_moneyline(x)))
df_filtered[['fighter1_after', 'fighter2_after']] = df_filtered['odds_after'].apply(lambda x: pd.Series(parse_moneyline(x)))

# Extract and sort by timestamp from file2
df_filtered['timestamp'] = pd.to_datetime(df_filtered['file2'].str.extract(r'_(\d{8}_\d{4})')[0], format='%Y%m%d_%H%M')
df_filtered = df_filtered.sort_values('timestamp').dropna(subset=['fighter1_after', 'fighter2_after'])

# Extract fighters
fighter1, fighter2 = selected_matchup.split(' vs ')

# Prepare data for plotting full line movement
times = df_filtered['timestamp'].tolist()
odds_f1 = [df_filtered.iloc[0]['fighter1_before']] + df_filtered['fighter1_after'].tolist()
odds_f2 = [df_filtered.iloc[0]['fighter2_before']] + df_filtered['fighter2_after'].tolist()
times_plot = [times[0]] + times

# Plot
plt.figure(figsize=(12, 6))
plt.plot(times_plot, odds_f1, label=fighter1, marker='o')
plt.plot(times_plot, odds_f2, label=fighter2, marker='x')
plt.title(f"{sportsbook_input} Odds Movement: {selected_matchup} on {selected_date}")
plt.ylabel('Odds (Moneyline)')
plt.xlabel('Timestamp')
plt.xticks(rotation=45)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# Final odds summary
print(f"\n📊 {sportsbook_input} Odds Movement Summary for {selected_matchup}")
print(f"{fighter1}: Started at {odds_f1[0]}, Ended at {odds_f1[-1]}")
print(f"{fighter2}: Started at {odds_f2[0]}, Ended at {odds_f2[-1]}")

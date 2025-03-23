# import pandas as pd
# import matplotlib.pyplot as plt

# # Load the dataset
# df = pd.read_csv("data/ufc_odds_movements.csv")

# # Get unique matchups and sort them
# matchups = sorted(df['matchup'].unique().tolist())

# # Display all matchups with numbers
# print("\n📋 Available Matchups:")
# for idx, matchup in enumerate(matchups, start=1):
#     print(f"{idx}. {matchup}")

# # Get user selection
# while True:
#     try:
#         choice = int(input("\nEnter the number of the matchup you'd like to analyze: "))
#         if 1 <= choice <= len(matchups):
#             selected_matchup = matchups[choice - 1]
#             break
#         else:
#             print("Please select a valid number.")
#     except ValueError:
#         print("Please enter a valid number.")

# # Ask for sportsbook
# sportsbook_input = input("Enter sportsbook (default is 'Circa'): ").strip() or "Circa"

# # Filter for selected matchup and sportsbook
# df = df[(df['matchup'] == selected_matchup) & (df['sportsbook'] == sportsbook_input)].copy()

# # Parse odds
# def parse_moneyline(odds_str):
#     try:
#         left, right = odds_str.split('|')
#         return float(left.strip().replace('+', '')), float(right.strip().replace('+', ''))
#     except:
#         return None, None

# df[['fighter1_before', 'fighter2_before']] = df.apply(lambda row: parse_moneyline(row['odds_before']), axis=1, result_type='expand')
# df[['fighter1_after', 'fighter2_after']] = df.apply(lambda row: parse_moneyline(row['odds_after']), axis=1, result_type='expand')
# df = df.dropna(subset=['fighter1_before', 'fighter1_after', 'fighter2_before', 'fighter2_after'])

# # Use the first valid entry
# row = df.iloc[0]

# # Extract fighter names
# fighter1, fighter2 = selected_matchup.split(' vs ')

# # Print odds values
# print(f"\n📊 {sportsbook_input} Odds for {selected_matchup}")
# print(f"{fighter1}: Before = {row['fighter1_before']}, After = {row['fighter1_after']}")
# print(f"{fighter2}: Before = {row['fighter2_before']}, After = {row['fighter2_after']}")

# # Plot odds movement
# plt.figure(figsize=(10, 6))
# plt.plot(['Before', 'After'], [row['fighter1_before'], row['fighter1_after']], label=fighter1, marker='o')
# plt.plot(['Before', 'After'], [row['fighter2_before'], row['fighter2_after']], label=fighter2, marker='x')
# plt.title(f"{sportsbook_input} Odds Movement: {selected_matchup}")
# plt.ylabel('Odds (Moneyline)')
# plt.legend()
# plt.grid(True)
# plt.tight_layout()
# plt.show()


import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt
import re

# Load data
df = pd.read_csv("data/ufc_odds_movements.csv")

# Step 1: Let user pick a game date
# dates = sorted(df['game_date'].unique().tolist())
# print("\n📆 Available Game Dates:")
# for idx, date in enumerate(dates, start=1):
#     print(f"{idx}. {date}")

# Function to clean and convert game_date to datetime
def parse_game_date(date_str):
    month_day = re.sub(r'(st|nd|rd|th)', '', date_str.split(',')[1].strip())
    return dt.datetime.strptime(f"2025 {month_day}", "%Y %B %d")

# Create a list of tuples (original_str, parsed_date)
dates_raw = df['game_date'].unique().tolist()
dates_parsed = [(d, parse_game_date(d)) for d in dates_raw]
dates_sorted = sorted(dates_parsed, key=lambda x: x[1])

# Extract only original strings, now chronologically ordered
dates = [d[0] for d in dates_sorted]

# Print the sorted game dates
print("\n📆 Available Game Dates (Chronological):")
for idx, date in enumerate(dates, start=1):
    print(f"{idx}. {date}")


while True:
    try:
        date_choice = int(input("\nSelect a game date by number: "))
        if 1 <= date_choice <= len(dates):
            selected_date = dates[date_choice - 1]
            break
        else:
            print("Please select a valid number.")
    except ValueError:
        print("Please enter a valid number.")

# Step 2: Filter matchups for selected date
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
        else:
            print("Please select a valid number.")
    except ValueError:
        print("Please enter a valid number.")

# Step 3: Get sportsbook
sportsbook_input = input("Enter sportsbook (default is 'Circa'): ").strip() or "Circa"

# Filter dataset for selected matchup and sportsbook
df_filtered = df_date[(df_date['matchup'] == selected_matchup) & (df_date['sportsbook'] == sportsbook_input)].copy()

# Parse moneyline odds
def parse_moneyline(odds_str):
    try:
        left, right = odds_str.split('|')
        return float(left.strip().replace('+', '')), float(right.strip().replace('+', ''))
    except:
        return None, None

df_filtered[['fighter1_before', 'fighter2_before']] = df_filtered.apply(lambda row: parse_moneyline(row['odds_before']), axis=1, result_type='expand')
df_filtered[['fighter1_after', 'fighter2_after']] = df_filtered.apply(lambda row: parse_moneyline(row['odds_after']), axis=1, result_type='expand')
df_filtered = df_filtered.dropna(subset=['fighter1_before', 'fighter1_after', 'fighter2_before', 'fighter2_after'])

# Use first valid odds row
row = df_filtered.iloc[0]
fighter1, fighter2 = selected_matchup.split(' vs ')

# Print odds
print(f"\n📊 {sportsbook_input} Odds for {selected_matchup}")
print(f"{fighter1}: Before = {row['fighter1_before']}, After = {row['fighter1_after']}")
print(f"{fighter2}: Before = {row['fighter2_before']}, After = {row['fighter2_after']}")

# Plot odds movement
plt.figure(figsize=(10, 6))
plt.plot(['Before', 'After'], [row['fighter1_before'], row['fighter1_after']], label=fighter1, marker='o')
plt.plot(['Before', 'After'], [row['fighter2_before'], row['fighter2_after']], label=fighter2, marker='x')
plt.title(f"{sportsbook_input} Odds Movement: {selected_matchup} on {selected_date}")
plt.ylabel('Odds (Moneyline)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

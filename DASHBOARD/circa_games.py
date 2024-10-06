import pandas as pd
import matplotlib.pyplot as plt

file_path = 'data/nfl_odds_movements.csv'
nfl_odds_data = pd.read_csv(file_path)

sportsbook = "Circa"
team1 = "Las Vegas Raiders"
team2 = "Denver Broncos"
# team1, team2 = "Chicago Bears", "Carolina Panthers"
# team1, team2 = "Baltimore Ravens", "Cincinnati Bengals"
# team1, team2 = "Buffalo Bills", "Houston Texans"
# team1, team2 = "Indianapolis Colts", "Jacksonville Jaguars"
# team1, team2 = "Miami Dolphins", "New England Patriots"
# team1, team2 = "Cleveland Browns", "Washington Commanders"
# team1, team2 = "San Francisco 49ers", "Arizona Cardinals"
# team1, team2 = "Green Bay Packers", "Los Angeles Rams"
# team1, team2 = "New York Giants", "Seattle Seahawks"
# team1, team2 = "Dallas Cowboys", "Pittsburgh Steelers"
# team1, team2 = "Kansas City Chiefs", "New Orleans Saints"

filtered_data = nfl_odds_data[
    (nfl_odds_data['team_1'].str.contains(team1, case=False)) &
    (nfl_odds_data['team_2'].str.contains(team2, case=False)) &
    (nfl_odds_data['sportsbook'] == sportsbook)
]

# Convert time_after to datetime, with error handling
filtered_data['time_after'] = pd.to_datetime(filtered_data['time_after'], format='%b %d %I:%M%p', errors='coerce')

# Check if conversion was successful
if filtered_data['time_after'].isnull().all():
    print("Warning: Failed to convert time_after to datetime. Using original strings for x-axis labels.")
    time_labels = filtered_data['time_after']
else:
    time_labels = filtered_data['time_after'].dt.strftime('%m-%d %H:%M')

# Convert odds to numeric
filtered_data['team1_odds_after'] = pd.to_numeric(filtered_data['team1_odds_after'], errors='coerce')
filtered_data['team2_odds_after'] = pd.to_numeric(filtered_data['team2_odds_after'], errors='coerce')

# Print all rows of filtered data
print(filtered_data.to_string())

# Plot for team2
plt.figure(figsize=(10, 6))
plt.plot(range(len(filtered_data)), filtered_data['team2_odds_after'], marker='o', linestyle='-')
plt.xlabel('Data Points')
plt.ylabel(f'{team2} Spread')
plt.title(f'{team2} Spread Movement ({sportsbook})')
plt.xticks(range(len(filtered_data)), time_labels, rotation=45, ha='right')
plt.tight_layout()
plt.show()

# Plot for team1
plt.figure(figsize=(10, 6))
plt.plot(range(len(filtered_data)), filtered_data['team1_odds_after'], marker='o', linestyle='-')
plt.xlabel('Data Points')
plt.ylabel(f'{team1} Spread')
plt.title(f'{team1} Spread Movement ({sportsbook})')
plt.xticks(range(len(filtered_data)), time_labels, rotation=45, ha='right')
plt.tight_layout()
plt.show()

# Combined plot for both teams
plt.figure(figsize=(12, 6))
plt.plot(range(len(filtered_data)), filtered_data['team1_odds_after'], marker='o', linestyle='-', label=team1)
plt.plot(range(len(filtered_data)), filtered_data['team2_odds_after'], marker='s', linestyle='-', label=team2)
plt.xlabel('Data Points')
plt.ylabel('Spread')
plt.title(f'{team1} vs {team2} Spread Movement ({sportsbook})')
plt.xticks(range(len(filtered_data)), time_labels, rotation=45, ha='right')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()
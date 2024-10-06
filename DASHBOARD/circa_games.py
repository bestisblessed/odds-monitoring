import pandas as pd
import matplotlib.pyplot as plt

file_path = 'data/nfl_odds_movements.csv'
nfl_odds_data = pd.read_csv(file_path)

team1 = "Las Vegas Raiders"
team2 = "Denver Broncos"
sportsbook = "Circa"

filtered_data = nfl_odds_data[
    (nfl_odds_data['team_1'].str.contains(team1, case=False)) &
    (nfl_odds_data['team_2'].str.contains(team2, case=False)) &
    (nfl_odds_data['sportsbook'] == sportsbook)
]
filtered_data.loc[:, 'time_after'] = pd.to_datetime(filtered_data['time_after'], format='%b %d %I:%M%p')
filtered_data.loc[:, 'team1_odds_after'] = pd.to_numeric(filtered_data['team1_odds_after'], errors='coerce')
filtered_data.loc[:, 'team2_odds_after'] = pd.to_numeric(filtered_data['team2_odds_after'], errors='coerce')

# Plot for Broncos
plt.figure(figsize=(10, 6))
plt.plot(filtered_data['time_after'], filtered_data['team2_odds_after'], marker='o', linestyle='-')
plt.xlabel('Time')
plt.ylabel('Broncos Spread')
plt.title('Broncos Spread Movement Over Time (Circa)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Plot for Raiders
plt.figure(figsize=(10, 6))
plt.plot(filtered_data['time_after'], filtered_data['team1_odds_after'], marker='o', linestyle='-')
plt.xlabel('Time')
plt.ylabel('Raiders Spread')
plt.title('Raiders Spread Movement Over Time (Circa)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Combined plot for Raiders and Broncos
plt.figure(figsize=(12, 6))
plt.plot(filtered_data['time_after'], filtered_data['team1_odds_after'], marker='o', linestyle='-', label='Raiders')
plt.plot(filtered_data['time_after'], filtered_data['team2_odds_after'], marker='s', linestyle='-', label='Broncos')
plt.xlabel('Time')
plt.ylabel('Spread')
plt.title(f'{team1} vs {team2} Spread Movement Over Time ({sportsbook})')
plt.xticks(rotation=45)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()

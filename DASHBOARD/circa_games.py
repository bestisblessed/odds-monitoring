import pandas as pd

# Load the dataset
file_path = 'data/nfl_odds_movements.csv'
nfl_odds_data = pd.read_csv(file_path)

# Example teams
team1 = "Las Vegas Raiders"
team2 = "Denver Broncos"

# Filter for rows where the matchup contains both teams and the sportsbook is "Circa"
filtered_data = nfl_odds_data[
    (nfl_odds_data['matchup'].str.contains(team1, case=False)) &
    (nfl_odds_data['matchup'].str.contains(team2, case=False)) &
    (nfl_odds_data['sportsbook'] == 'Circa')
]

# Print the result
print(filtered_data)

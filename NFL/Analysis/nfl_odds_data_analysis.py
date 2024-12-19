import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import os  
csv_file = 'data/nfl_odds_movements_circa.csv'
df = pd.read_csv(csv_file)
unique_matchups = df['team_1'] + ' vs ' + df['team_2']
unique_matchups = unique_matchups.unique()
print("All unique matchups:")
for matchup in sorted(unique_matchups):
    print(matchup)
pdf_filename = 'data/nfl_odds_movements.pdf'  # Updated pdf_filename to save in 'data' directory
with PdfPages(pdf_filename) as pdf:
    for target_game in unique_matchups:
        game_df = df[
            (df['team_1'] + ' vs ' + df['team_2'] == target_game) &
            (df['team1_odds_before'] != '-') &
            (df['team2_odds_before'] != '-')
        ].copy()
        game_df.loc[:, 'time_before'] = pd.to_datetime(game_df['time_before'], 
                                                       format='%b %d %I:%M%p', 
                                                       errors='coerce')
        game_df = game_df.sort_values('time_before')
        team1, team2 = target_game.split(' vs ')
        print(f"\n{team1} vs {team2} Line Movements:")
        print("-" * 50)
        first = True
        times = []
        odds_team1 = []
        odds_team2 = []
        for _, row in game_df.iterrows():
            if pd.notna(row['time_before']):
                time = row['time_before'].strftime('%b %d %I:%M%p')
                try:
                    odds1 = float(row['team1_odds_before'])
                    odds2 = float(row['team2_odds_before'])
                    note = " (Opening line)" if first else ""
                    print(f"{time}: {team1} {odds1:+.1f}, {team2} {odds2:+.1f}{note}")
                    first = False
                    times.append(row['time_before'])
                    odds_team1.append(odds1)
                    odds_team2.append(odds2)
                except (ValueError, TypeError):
                    continue
        plt.figure(figsize=(10, 6))
        plt.plot(times, odds_team1, label=f'{team1} Odds', marker='o')
        plt.plot(times, odds_team2, label=f'{team2} Odds', marker='o')
        plt.title(f'{team1} vs {team2} Line Movements')
        plt.xlabel('Time')
        plt.ylabel('Odds')
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        pdf.savefig()
        plt.close()
os.system(f'open {pdf_filename}')  

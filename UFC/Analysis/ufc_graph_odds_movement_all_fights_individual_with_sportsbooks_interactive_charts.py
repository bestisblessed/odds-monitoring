import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load UFC odds movements CSV
file_path = "data/ufc_odds_movements.csv"  # Adjust this path as needed
ufc_odds_data = pd.read_csv(file_path)

# Ensure column names are correct
ufc_odds_data.rename(columns={'game_date': 'fight_date', 'game_time': 'fight_time'}, inplace=True)

# Split matchup into two fighter names
ufc_odds_data[['fighter_1', 'fighter_2']] = ufc_odds_data['matchup'].str.split(' vs ', expand=True)

# Split the odds into separate fighter odds columns
ufc_odds_data[['fighter1_odds_before', 'fighter2_odds_before']] = ufc_odds_data['odds_before'].str.split(r'\s+\|\s+', expand=True)
ufc_odds_data[['fighter1_odds_after', 'fighter2_odds_after']] = ufc_odds_data['odds_after'].str.split(r'\s+\|\s+', expand=True)

# Convert odds columns to numeric
odds_columns = ['fighter1_odds_before', 'fighter2_odds_before', 'fighter1_odds_after', 'fighter2_odds_after']
for col in odds_columns:
    ufc_odds_data[col] = pd.to_numeric(ufc_odds_data[col], errors='coerce')

# Get unique sportsbooks
sportsbooks = ufc_odds_data['sportsbook'].unique()

# Add this missing line to get unique fights
unique_fights = ufc_odds_data[['fighter_1', 'fighter_2']].drop_duplicates()

# Replace PDF path with HTML directory
output_dir = "interactive_odds_graphs"
os.makedirs(output_dir, exist_ok=True)

# Remove PDF creation block and replace with interactive plotting
for _, row in unique_fights.iterrows():
    fight_data = ufc_odds_data[(ufc_odds_data['fighter_1'] == row['fighter_1']) & 
                               (ufc_odds_data['fighter_2'] == row['fighter_2'])]

    if fight_data.empty:
        continue

    for sportsbook in sportsbooks:
        fight_sportsbook_data = fight_data[fight_data['sportsbook'] == sportsbook]
        
        if fight_sportsbook_data.empty:
            continue

        fight_sportsbook_data = fight_sportsbook_data.sort_values(by=['fight_date', 'fight_time'])
        
        # Create interactive plot
        fig = go.Figure()
        x_vals = fight_sportsbook_data.index
        
        # Add traces for each odds series
        fig.add_trace(go.Scatter(x=x_vals, y=fight_sportsbook_data['fighter1_odds_before'],
                             mode='lines+markers', name=f"{row['fighter_1']} Before"))
        fig.add_trace(go.Scatter(x=x_vals, y=fight_sportsbook_data['fighter1_odds_after'],
                             mode='lines+markers', name=f"{row['fighter_1']} After"))
        fig.add_trace(go.Scatter(x=x_vals, y=fight_sportsbook_data['fighter2_odds_before'],
                             mode='lines+markers', name=f"{row['fighter_2']} Before"))
        fig.add_trace(go.Scatter(x=x_vals, y=fight_sportsbook_data['fighter2_odds_after'],
                             mode='lines+markers', name=f"{row['fighter_2']} After"))

        # Update layout
        fig.update_layout(
            title=f"Odds Movement: {row['fighter_1']} vs {row['fighter_2']} ({sportsbook})",
            xaxis_title='Observation Index',
            yaxis_title='Odds',
            hovermode='x unified',
            showlegend=True
        )
        
        # Save as HTML
        safe_fighter_names = f"{row['fighter_1']}_vs_{row['fighter_2']}".replace(' ', '_')
        filename = f"{output_dir}/{safe_fighter_names}_{sportsbook}.html"
        fig.write_html(filename)

print(f"Interactive graphs saved to {output_dir}/ directory")

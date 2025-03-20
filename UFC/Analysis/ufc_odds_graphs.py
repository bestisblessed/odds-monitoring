import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import re

# Load UFC odds movements CSV
file_path = "data/ufc_odds_movements.csv"  # Adjust this path as needed
ufc_odds_data = pd.read_csv(file_path)

# Ensure column names are correct
ufc_odds_data.rename(columns={'game_date': 'fight_date', 'game_time': 'fight_time'}, inplace=True)

# Split matchup into two fighter names
ufc_odds_data[['fighter_1', 'fighter_2']] = ufc_odds_data['matchup'].str.split(' vs ', expand=True)

# Replace direct splitting of odds with safe splitting to avoid errors when one part is missing
def safe_split(s):
    if pd.isna(s):
        return [None, None]
    parts = re.split(r'\s+\|\s+', s)
    if len(parts) < 2:
        parts.append(None)
    return parts[:2]

# Split the odds into separate fighter odds columns
ufc_odds_data[['fighter1_odds_before', 'fighter2_odds_before']] = ufc_odds_data['odds_before'].apply(safe_split).tolist()
ufc_odds_data[['fighter1_odds_after', 'fighter2_odds_after']] = ufc_odds_data['odds_after'].apply(safe_split).tolist()

# Convert odds columns to numeric
odds_columns = [
    'fighter1_odds_before',
    'fighter2_odds_before',
    'fighter1_odds_after',
    'fighter2_odds_after'
]
for col in odds_columns:
    ufc_odds_data[col] = pd.to_numeric(ufc_odds_data[col], errors='coerce')

# Get unique sportsbooks
sportsbooks = ufc_odds_data['sportsbook'].unique()

# Define the output PDF file
pdf_file_path = "UFC_ODDS_MOVEMENT_GRAPHS.pdf"

# Create a PDF to save all plots
with PdfPages(pdf_file_path) as pdf:
    # Identify each unique fight
    unique_fights = ufc_odds_data[['fighter_1', 'fighter_2']].drop_duplicates()

    for _, row in unique_fights.iterrows():
        fight_data = ufc_odds_data[
            (ufc_odds_data['fighter_1'] == row['fighter_1']) &
            (ufc_odds_data['fighter_2'] == row['fighter_2'])
        ]

        if fight_data.empty:
            continue

        # Create a separate figure for each sportsbook
        for sportsbook in sportsbooks:
            fight_sportsbook_data = fight_data[fight_data['sportsbook'] == sportsbook]
            if fight_sportsbook_data.empty:
                continue

            # Sort data by time
            fight_sportsbook_data = fight_sportsbook_data.sort_values(by=['fight_date', 'fight_time'])

            # Plot only the AFTER odds for each fighter
            plt.figure(figsize=(10, 5))
            plt.plot(
                fight_sportsbook_data.index,
                fight_sportsbook_data['fighter1_odds_after'],
                marker='s',
                linestyle='-',
                label=f"{row['fighter_1']} (After)"
            )
            plt.plot(
                fight_sportsbook_data.index,
                fight_sportsbook_data['fighter2_odds_after'],
                marker='s',
                linestyle='-',
                label=f"{row['fighter_2']} (After)"
            )

            plt.xlabel("Fight Event Index")
            plt.ylabel("Odds")
            plt.title(f"Odds Movement: {row['fighter_1']} vs {row['fighter_2']} ({sportsbook})")
            plt.legend()
            plt.grid(True)

            # Save the plot to the PDF
            pdf.savefig()
            plt.close()

print(f"Graphs saved to {pdf_file_path}")


# import os
# import pandas as pd
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_pdf import PdfPages

# # Load UFC odds movements CSV
# file_path = "data/ufc_odds_movements.csv"  # Adjust this path as needed
# ufc_odds_data = pd.read_csv(file_path)

# # Ensure column names are correct
# ufc_odds_data.rename(columns={'game_date': 'fight_date', 'game_time': 'fight_time'}, inplace=True)

# # Split matchup into two fighter names
# ufc_odds_data[['fighter_1', 'fighter_2']] = ufc_odds_data['matchup'].str.split(' vs ', expand=True)

# # Split the odds into separate fighter odds columns
# ufc_odds_data[['fighter1_odds_before', 'fighter2_odds_before']] = \
#     ufc_odds_data['odds_before'].str.split(r'\\s+\\|\\s+', expand=True)
# ufc_odds_data[['fighter1_odds_after', 'fighter2_odds_after']] = \
#     ufc_odds_data['odds_after'].str.split(r'\\s+\\|\\s+', expand=True)

# # Convert odds columns to numeric
# odds_columns = [
#     'fighter1_odds_before',
#     'fighter2_odds_before',
#     'fighter1_odds_after',
#     'fighter2_odds_after'
# ]
# for col in odds_columns:
#     ufc_odds_data[col] = pd.to_numeric(ufc_odds_data[col], errors='coerce')

# # Get unique sportsbooks
# sportsbooks = ufc_odds_data['sportsbook'].unique()

# # Define the output PDF file
# pdf_file_path = "UFC_ODDS_MOVEMENT_GRAPHS.pdf"

# # Create a PDF to save all plots
# with PdfPages(pdf_file_path) as pdf:
#     # Identify each unique fight
#     unique_fights = ufc_odds_data[['fighter_1', 'fighter_2']].drop_duplicates()

#     for _, row in unique_fights.iterrows():
#         fight_data = ufc_odds_data[
#             (ufc_odds_data['fighter_1'] == row['fighter_1']) &
#             (ufc_odds_data['fighter_2'] == row['fighter_2'])
#         ]

#         if fight_data.empty:
#             continue

#         # Create a separate figure for each sportsbook
#         for sportsbook in sportsbooks:
#             fight_sportsbook_data = fight_data[fight_data['sportsbook'] == sportsbook]
#             if fight_sportsbook_data.empty:
#                 continue

#             # Sort data by time
#             fight_sportsbook_data = fight_sportsbook_data.sort_values(by=['fight_date', 'fight_time'])

#             # Plot only the AFTER odds for each fighter
#             plt.figure(figsize=(10, 5))
#             plt.plot(
#                 fight_sportsbook_data.index,
#                 fight_sportsbook_data['fighter1_odds_after'],
#                 marker='s',
#                 linestyle='-',
#                 label=f"{row['fighter_1']} (After)"
#             )
#             plt.plot(
#                 fight_sportsbook_data.index,
#                 fight_sportsbook_data['fighter2_odds_after'],
#                 marker='s',
#                 linestyle='-',
#                 label=f"{row['fighter_2']} (After)"
#             )

#             plt.xlabel("Fight Event Index")
#             plt.ylabel("Odds")
#             plt.title(f"Odds Movement: {row['fighter_1']} vs {row['fighter_2']} ({sportsbook})")
#             plt.legend()
#             plt.grid(True)

#             # Save the plot to the PDF
#             pdf.savefig()
#             plt.close()

# print(f"Graphs saved to {pdf_file_path}")

# # import dash
# # from dash import dcc, html, Input, Output, State, MATCH
# # import dash_bootstrap_components as dbc
# # import json
# # import os

# # # Initialize Dash with Bootstrap stylesheet
# # app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# # # Load data from JSON files
# # def load_games_data():
# #     games_data = []
    
# #     # Directory where your JSON files are located
# #     data_dir = os.path.join(os.path.dirname(__file__), 'data')
    
# #     # Get all JSON files and sort them by their timestamp (assuming the filenames include a timestamp)
# #     json_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".json")], reverse=True)
    
# #     # Use the most recent file (the first in the sorted list)
# #     most_recent_file = json_files[0] if json_files else None
    
# #     # If a file is found, load data from it
# #     if most_recent_file:
# #         filepath = os.path.join(data_dir, most_recent_file)
# #         with open(filepath) as f:
# #             data = json.load(f)
# #             for game in data:
# #                 game_time = game['Time'].replace('\n', '').strip()  # Clean up the time
# #                 day_and_matchup = list(game.keys())[1]  # The second column contains the teams/matchup
# #                 day_and_matchup_column_name = list(game.keys())[1].replace(',', ', ')
# #                 teams = game[day_and_matchup].replace('\n', ' ').strip()  # Clean up the teams

# #                 # Extract the "Circa" spread and use it dynamically
# #                 circa_spread = game.get("Circa", "").replace('\n', ' ').strip().split(' ')
# #                 if len(circa_spread) == 4:
# #                     # First two values for the favorite and last two for the underdog
# #                     spread_favorite = f"{circa_spread[0]} {circa_spread[1]}"
# #                     spread_underdog = f"{circa_spread[2]} {circa_spread[3]}"
# #                 else:
# #                     # Default if Circa spread data is missing or not formatted as expected
# #                     spread_favorite = "N/A"
# #                     spread_underdog = "N/A"

# #                 # Add the extracted data to the games_data list
# #                 games_data.append({
# #                     'time': game_time,
# #                     'day_and_matchup_column_name': day_and_matchup_column_name,
# #                     'teams': teams.split('  '),  # Split into two teams
# #                     'spread': [spread_favorite, spread_underdog],  # Use Circa spread
# #                     'moneyline': ['N/A', 'N/A'],       # Placeholder, replace dynamically if needed
# #                     # 'total': ['O 45 -110', 'U 45 -110']  # Placeholder, replace dynamically if needed
# #                     'total': ['N/A', 'N/A']  # Placeholder, replace dynamically if needed
# #                 })
# #     return games_data

# # games_data = load_games_data()

# # app.layout = html.Div([
# #     html.H1("NFL Odds Dashboard", style={'text-align': 'center'}),
    
# #     html.Div([
# #         html.Div([
# #             html.H3(game['time']),
# #             html.H3(game['day_and_matchup_column_name']),
# #             html.Table([
# #                 html.Tr([
# #                     html.Th("Team"),
# #                     html.Th("Spread"),
# #                     html.Th("Moneyline"),
# #                     html.Th("Total")
# #                 ]),
# #                 html.Tr([
# #                     html.Td(game['teams'][0]),
# #                     html.Td(
# #                         dbc.Button(
# #                             game['spread'][0],
# #                             id={'type': 'open-modal', 'index': f"{game['teams'][0]}-{i}"},
# #                             n_clicks=0,
# #                             color="info"
# #                         )
# #                     ),
# #                     html.Td(game['moneyline'][0]),
# #                     html.Td(game['total'][0])
# #                 ]),
# #                 html.Tr([
# #                     html.Td(game['teams'][1]),
# #                     html.Td(
# #                         dbc.Button(
# #                             game['spread'][1],
# #                             id={'type': 'open-modal', 'index': f"{game['teams'][1]}-{i}"},
# #                             n_clicks=0,
# #                             color="info"
# #                         )
# #                     ),
# #                     html.Td(game['moneyline'][1]),
# #                     html.Td(game['total'][1])
# #                 ])
# #             ], style={'width': '100%', 'border': '1px solid black', 'text-align': 'center'}),
# #             # Modals for Each Team's Spread
# #             dbc.Modal(
# #                 [
# #                     dbc.ModalHeader(dbc.ModalTitle(f"{game['teams'][0]} Spread Details")),
# #                     dbc.ModalBody(f"Details about {game['teams'][0]} spread.")
# #                 ],
# #                 id={'type': 'modal', 'index': f"{game['teams'][0]}-{i}"},
# #                 is_open=False
# #             ),
# #             dbc.Modal(
# #                 [
# #                     dbc.ModalHeader(dbc.ModalTitle(f"{game['teams'][1]} Spread Details")),
# #                     dbc.ModalBody(f"Details about {game['teams'][1]} spread.")
# #                 ],
# #                 id={'type': 'modal', 'index': f"{game['teams'][1]}-{i}"},
# #                 is_open=False
# #             )
# #         ], style={'margin': '20px', 'border': '1px solid black', 'padding': '20px'})
# #         for i, game in enumerate(games_data)
# #     ])
# # ])

# # @app.callback(
# #     Output({'type': 'modal', 'index': MATCH}, 'is_open'),
# #     Input({'type': 'open-modal', 'index': MATCH}, 'n_clicks'),
# #     State({'type': 'modal', 'index': MATCH}, 'is_open')
# # )
# # def toggle_modal(n_clicks, is_open):
# #     if n_clicks:
# #         return not is_open
# #     return is_open

# # if __name__ == '__main__':
# #     app.run_server(debug=True)






# # # import dash
# # # from dash import dcc, html
# # # import json
# # # import os
# # # import dash_bootstrap_components as dbc
# # # from dash import dcc, html, Input, Output, State, callback_context


# # # # Initialize Dash
# # # app = dash.Dash(__name__)

# # # # Load data from JSON files in the "data/" directory
# # # # Load data from the most recent JSON file in the "data/" directory
# # # def load_games_data():
# # #     games_data = []
    
# # #     # Directory where your JSON files are located
# # #     data_dir = os.path.join(os.path.dirname(__file__), 'data')
    
# # #     # Get all JSON files and sort them by their timestamp (assuming the filenames include a timestamp)
# # #     json_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".json")], reverse=True)
    
# # #     # Use the most recent file (the first in the sorted list)
# # #     most_recent_file = json_files[0] if json_files else None
    
# # #     # If a file is found, load data from it
# # #     if most_recent_file:
# # #         filepath = os.path.join(data_dir, most_recent_file)
# # #         with open(filepath) as f:
# # #             data = json.load(f)
# # #             for game in data:
# # #                 game_time = game['Time'].replace('\n', '').strip()  # Clean up the time
# # #                 day_and_matchup = list(game.keys())[1]  # The second column contains the teams/matchup
# # #                 day_and_matchup_column_name = list(game.keys())[1].replace(',', ', ')
# # #                 teams = game[day_and_matchup].replace('\n', ' ').strip()  # Clean up the teams

# # #                 # Extract the "Circa" spread and use it dynamically
# # #                 circa_spread = game.get("Circa", "").replace('\n', ' ').strip().split(' ')
# # #                 if len(circa_spread) == 4:
# # #                     # First two values for the favorite and last two for the underdog
# # #                     spread_favorite = f"{circa_spread[0]} {circa_spread[1]}"
# # #                     spread_underdog = f"{circa_spread[2]} {circa_spread[3]}"
# # #                 else:
# # #                     # Default if Circa spread data is missing or not formatted as expected
# # #                     spread_favorite = "N/A"
# # #                     spread_underdog = "N/A"

# # #                 # Add the extracted data to the games_data list
# # #                 games_data.append({
# # #                     'time': game_time,
# # #                     'day_and_matchup_column_name': day_and_matchup_column_name,
# # #                     'teams': teams.split('  '),  # Split into two teams
# # #                     'spread': [spread_favorite, spread_underdog],  # Use Circa spread
# # #                     'moneyline': ['N/A', 'N/A'],       # Placeholder, replace dynamically if needed
# # #                     # 'total': ['O 45 -110', 'U 45 -110']  # Placeholder, replace dynamically if needed
# # #                     'total': ['N/A', 'N/A']  # Placeholder, replace dynamically if needed
# # #                 })
# # #     return games_data

# # # # Define games_data based on the files in the data directory
# # # games_data = load_games_data()

# # # # app.layout = html.Div([
# # # #     html.H1("NFL Odds Dashboard", style={'text-align': 'center'}),
    
# # # #     # Loop through games_data and create sections for each game
# # # #     html.Div([
# # # #         html.Div([
# # # #             html.H3(game['time']),
# # # #             html.H3(game['day_and_matchup_column_name']),
# # # #             html.Table([
# # # #                 # Header
# # # #                 html.Tr([
# # # #                     html.Th("Team"),
# # # #                     html.Th("Spread"),
# # # #                     html.Th("Moneyline"),
# # # #                     html.Th("Total")
# # # #                 ]),
# # # #                 html.Tr([
# # # #                     html.Td(game['teams'][0], style={'text-align': 'center'}),  # Center team name
                    
# # # #                     # First team spread dropdown, centered
# # # #                     html.Td(dcc.Dropdown(
# # # #                         id=f'spread-dropdown-{game["teams"][0]}',
# # # #                         options=[{'label': game['spread'][0], 'value': game['spread'][0]}],
# # # #                         value=game['spread'][0],
# # # #                         clearable=False,
# # # #                         style={'width': '125px', 'margin': 'auto'}  # Center the dropdown
# # # #                     ), style={'text-align': 'center'}),  # Center the table cell
                    
# # # #                     html.Td(game['moneyline'][0], style={'text-align': 'center'}),
# # # #                     html.Td(game['total'][0], style={'text-align': 'center'})
# # # #                 ]),
# # # #                 html.Tr([
# # # #                     html.Td(game['teams'][1], style={'text-align': 'center'}),  # Center team name
                    
# # # #                     # Second team spread dropdown, centered
# # # #                     html.Td(dcc.Dropdown(
# # # #                         id=f'spread-dropdown-{game["teams"][1]}',
# # # #                         options=[{'label': game['spread'][1], 'value': game['spread'][1]}],
# # # #                         value=game['spread'][1],
# # # #                         clearable=False,
# # # #                         style={'width': '125px', 'margin': 'auto'}  # Center the dropdown
# # # #                     ), style={'text-align': 'center'}),  # Center the table cell
                    
# # # #                     html.Td(game['moneyline'][1], style={'text-align': 'center'}),
# # # #                     html.Td(game['total'][1], style={'text-align': 'center'})
# # # #                 ])
# # # #             ], style={'width': '100%', 'border': '1px solid black', 'text-align': 'center'})
# # # #         ], style={'margin': '20px', 'border': '1px solid black', 'padding': '20px'})
# # # #         for game in games_data
# # # #     ])
# # # # ])
# # # # Define layout for the app
# # # app.layout = html.Div([
# # #     html.H1("NFL Odds Dashboard", style={'text-align': 'center'}),
    
# # #     # Loop through games_data and create sections for each game
# # #     html.Div([
# # #         html.Div([
# # #             html.H3(game['time']),
# # #             html.H3(game['day_and_matchup_column_name']),
# # #             html.Table([
# # #                 # Header
# # #                 html.Tr([
# # #                     html.Th("Team"),
# # #                     html.Th("Spread"),
# # #                     html.Th("Moneyline"),
# # #                     html.Th("Total")
# # #                 ]),
# # #                 # First team row
# # #                 html.Tr([
# # #                     html.Td(game['teams'][0]),
# # #                     html.Td(game['spread'][0]),
# # #                     html.Td(game['moneyline'][0]),
# # #                     html.Td(game['total'][0])
# # #                 ]),
# # #                 # Second team row
# # #                 html.Tr([
# # #                     html.Td(game['teams'][1]),
# # #                     html.Td(game['spread'][1]),
# # #                     html.Td(game['moneyline'][1]),
# # #                     html.Td(game['total'][1])
# # #                 ])
# # #             ], style={'width': '100%', 'border': '1px solid black', 'text-align': 'center'})
# # #         ], style={'margin': '20px', 'border': '1px solid black', 'padding': '20px'})
# # #         for game in games_data
# # #     ])
# # # ])

# # # # Run the app
# # # if __name__ == '__main__':
# # #     app.run_server(debug=True)

# import dash
# from dash import dcc, html, Input, Output, State, MATCH
# import dash_bootstrap_components as dbc
# import pandas as pd
# import json
# import os

# # Initialize Dash with Bootstrap stylesheet
# app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# # Load odds movements data from the CSV file
# def load_odds_movements():
#     odds_movements = pd.read_csv('odds_movements.csv')

#     # Clean data
#     odds_movements['game_date'] = odds_movements['game_date'].str.strip().str.lower()
#     odds_movements['game_time'] = odds_movements['game_time'].str.replace('\n', ' ').str.strip().str.lower()
#     odds_movements['matchup'] = odds_movements['matchup'].str.replace('\\s+', ' ', regex=True).str.strip().str.lower()

#     return odds_movements

# odds_movements = load_odds_movements()

# # Load data from JSON files
# def load_games_data():
#     games_data = []

#     # Directory where your JSON files are located
#     data_dir = os.path.join(os.path.dirname(__file__), 'data')

#     # Get all JSON files and sort them by their timestamp (assuming the filenames include a timestamp)
#     json_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".json")], reverse=True)

#     # Use the most recent file (the first in the sorted list)
#     most_recent_file = json_files[0] if json_files else None

#     # If a file is found, load data from it
#     if most_recent_file:
#         filepath = os.path.join(data_dir, most_recent_file)
#         with open(filepath) as f:
#             data = json.load(f)
#             for game in data:
#                 # Clean up the time
#                 game_time = game['Time'].replace('\n', ' ').strip()

#                 # Extract the key that contains game_date and teams
#                 day_and_matchup_key = list(game.keys())[1]  # The second key
#                 day_and_matchup_value = game[day_and_matchup_key]

#                 # Extract game_date
#                 game_date = day_and_matchup_key.strip()

#                 # Extract teams
#                 teams = day_and_matchup_value.replace('\n', ' ').strip()
#                 teams_list = [team.strip() for team in teams.split('  ')]

#                 # Construct matchup
#                 matchup = ' vs '.join(teams_list)

#                 # Extract the "Circa" spread and use it dynamically
#                 circa_spread = game.get("Circa", "").replace('\n', ' ').strip().split(' ')
#                 if len(circa_spread) == 4:
#                     # First two values for the favorite and last two for the underdog
#                     spread_favorite = f"{circa_spread[0]} {circa_spread[1]}"
#                     spread_underdog = f"{circa_spread[2]} {circa_spread[3]}"
#                 else:
#                     # Default if Circa spread data is missing or not formatted as expected
#                     spread_favorite = "N/A"
#                     spread_underdog = "N/A"

#                 # Add the extracted data to the games_data list
#                 games_data.append({
#                     'time': game_time,
#                     'game_date': game_date,
#                     'matchup': matchup,
#                     'teams': teams_list,
#                     'spread': [spread_favorite, spread_underdog],  # Use Circa spread
#                     'moneyline': ['N/A', 'N/A'],       # Placeholder, replace dynamically if needed
#                     'total': ['N/A', 'N/A']            # Placeholder, replace dynamically if needed
#                 })
#     else:
#         print("No JSON files found in the data directory.")

#     return games_data

# games_data = load_games_data()

# app.layout = html.Div([
#     html.H1("NFL Odds Dashboard", style={'text-align': 'center'}),
    
#     html.Div([
#         html.Div([
#             html.H3(game['time']),
#             html.H3(game['game_date']),
#             html.Table([
#                 html.Tr([
#                     html.Th("Team"),
#                     html.Th("Spread"),
#                     html.Th("Moneyline"),
#                     html.Th("Total")
#                 ]),
#                 html.Tr([
#                     html.Td(game['teams'][0]),
#                     html.Td(
#                         dbc.Button(
#                             game['spread'][0],
#                             id={'type': 'open-modal', 'index': f"{game['teams'][0]}-{i}"},
#                             n_clicks=0,
#                             color="info"
#                         )
#                     ),
#                     html.Td(game['moneyline'][0]),
#                     html.Td(game['total'][0])
#                 ]),
#                 html.Tr([
#                     html.Td(game['teams'][1]),
#                     html.Td(
#                         dbc.Button(
#                             game['spread'][1],
#                             id={'type': 'open-modal', 'index': f"{game['teams'][1]}-{i}"},
#                             n_clicks=0,
#                             color="info"
#                         )
#                     ),
#                     html.Td(game['moneyline'][1]),
#                     html.Td(game['total'][1])
#                 ])
#             ], style={'width': '100%', 'border': '1px solid black', 'text-align': 'center'}),
#             # Modals for Each Team's Spread
#             dbc.Modal(
#                 [
#                     dbc.ModalHeader(dbc.ModalTitle(f"{game['teams'][0]} Spread Details")),
#                     dbc.ModalBody(id={'type': 'modal-body', 'index': f"{game['teams'][0]}-{i}"})
#                 ],
#                 id={'type': 'modal', 'index': f"{game['teams'][0]}-{i}"},
#                 is_open=False,
#                 size="xl",
#             ),
#             dbc.Modal(
#                 [
#                     dbc.ModalHeader(dbc.ModalTitle(f"{game['teams'][1]} Spread Details")),
#                     dbc.ModalBody(id={'type': 'modal-body', 'index': f"{game['teams'][1]}-{i}"})
#                 ],
#                 id={'type': 'modal', 'index': f"{game['teams'][1]}-{i}"},
#                 is_open=False,
#                 size="xl",
#             )
#         ], style={'margin': '20px', 'border': '1px solid black', 'padding': '20px'})
#         for i, game in enumerate(games_data)
#     ])
# ])

# # Callback to toggle modals and update modal content
# @app.callback(
#     [
#         Output({'type': 'modal', 'index': MATCH}, 'is_open'),
#         Output({'type': 'modal-body', 'index': MATCH}, 'children')
#     ],
#     Input({'type': 'open-modal', 'index': MATCH}, 'n_clicks'),
#     State({'type': 'modal', 'index': MATCH}, 'is_open')
# )
# def toggle_modal(n_clicks, is_open):
#     if n_clicks:
#         ctx = dash.callback_context
#         if not ctx.triggered:
#             return is_open, dash.no_update
#         else:
#             index = ctx.triggered[0]['prop_id'].split('.')[0]
#             index_dict = eval(index)
#             modal_index = index_dict['index']  # e.g., 'TeamName-i'

#             # Extract team name and game index
#             team_name, game_index = modal_index.rsplit('-', 1)
#             game_index = int(game_index)

#             # Get game data
#             game = games_data[game_index]
#             game_date = game['game_date']
#             game_time = game['time']
#             matchup = game['matchup']

#             # Clean and standardize strings
#             game_date_clean = game_date.strip().lower()
#             game_time_clean = game_time.replace('\n', ' ').strip().lower()
#             matchup_clean = matchup.strip().lower()
#             team_name_clean = team_name.strip().lower()

#             # Clean odds_movements columns
#             odds_movements_clean = odds_movements.copy()

#             # Filter odds_movements for relevant data
#             relevant_odds_movements = odds_movements_clean[
#                 (odds_movements_clean['game_date'] == game_date_clean) &
#                 (odds_movements_clean['game_time'] == game_time_clean) &
#                 (odds_movements_clean['matchup'] == matchup_clean)
#             ]

#             if not relevant_odds_movements.empty:
#                 # Create table of odds movements
#                 table_header = [
#                     html.Thead(html.Tr([html.Th(col) for col in relevant_odds_movements.columns]))
#                 ]
#                 rows = []
#                 for _, row in relevant_odds_movements.iterrows():
#                     rows.append(html.Tr([html.Td(row[col]) for col in relevant_odds_movements.columns]))
#                 table_body = [html.Tbody(rows)]
#                 table = dbc.Table(table_header + table_body, bordered=True)
#                 modal_body = table
#             else:
#                 modal_body = html.P("No odds movement data available for this game.")
#             return not is_open, modal_body
#     return is_open, dash.no_update

# if __name__ == '__main__':
#     app.run_server(debug=True)

import dash
from dash import dcc, html, Input, Output, State, MATCH
import dash_bootstrap_components as dbc
import pandas as pd
import json
import os
import re

# Initialize Dash with Bootstrap stylesheet
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Load odds movements data from the CSV file
def load_odds_movements():
    odds_movements = pd.read_csv('odds_movements.csv')

    # Clean data
    odds_movements['game_date'] = odds_movements['game_date'].str.replace(' ', '').str.strip().str.lower()
    odds_movements['game_time'] = odds_movements['game_time'].str.replace('\n', ' ').str.replace(r'\s+', ' ', regex=True).str.strip().str.lower()
    odds_movements['matchup'] = odds_movements['matchup'].str.replace(r'\s+', ' ', regex=True).str.strip().str.lower()

    return odds_movements

odds_movements = load_odds_movements()

# Load data from JSON files
def load_games_data():
    games_data = []

    # Directory where your JSON files are located
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    # Get all JSON files and sort them by their timestamp (assuming the filenames include a timestamp)
    json_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".json")], reverse=True)

    # Use the most recent file (the first in the sorted list)
    most_recent_file = json_files[0] if json_files else None

    # If a file is found, load data from it
    if most_recent_file:
        filepath = os.path.join(data_dir, most_recent_file)
        with open(filepath) as f:
            data = json.load(f)
            for game in data:
                # Clean up the time
                game_time = game['Time']

                # Extract the key that contains game_date and teams
                day_and_matchup_key = list(game.keys())[1]  # The second key
                day_and_matchup_value = game[day_and_matchup_key]

                # Extract game_date
                game_date = day_and_matchup_key.strip()

                # Extract teams
                teams = day_and_matchup_value.replace('\n', ' ').strip()
                teams_list = [team.strip() for team in teams.split('  ')]

                # Clean up the date and time
                game_date = game_date.replace(' ', '').strip().lower()
                game_time = re.sub(r'\s+', ' ', game_time.replace('\n', ' ')).strip().lower()

                # Construct matchup
                matchup = re.sub(r'\s+', ' ', ' vs '.join(teams_list)).strip().lower()

                # Extract the "Circa" spread and use it dynamically
                circa_spread = game.get("Circa", "").replace('\n', ' ').strip().split(' ')
                if len(circa_spread) == 4:
                    # First two values for the favorite and last two for the underdog
                    spread_favorite = f"{circa_spread[0]} {circa_spread[1]}"
                    spread_underdog = f"{circa_spread[2]} {circa_spread[3]}"
                else:
                    # Default if Circa spread data is missing or not formatted as expected
                    spread_favorite = "N/A"
                    spread_underdog = "N/A"

                # Add the extracted data to the games_data list
                games_data.append({
                    'time': game_time,
                    'game_date': game_date,
                    'matchup': matchup,
                    'teams': teams_list,
                    'spread': [spread_favorite, spread_underdog],  # Use Circa spread
                    'moneyline': ['N/A', 'N/A'],       # Placeholder, replace dynamically if needed
                    'total': ['N/A', 'N/A']            # Placeholder, replace dynamically if needed
                })
    else:
        print("No JSON files found in the data directory.")

    return games_data

games_data = load_games_data()

app.layout = html.Div([
    html.H1("NFL Odds Dashboard", style={'text-align': 'center'}),

    html.Div([
        html.Div([
            html.H3(game['time']),
            html.H3(game['game_date']),
            html.Table([
                html.Tr([
                    html.Th("Team"),
                    html.Th("Spread"),
                    html.Th("Moneyline"),
                    html.Th("Total")
                ]),
                html.Tr([
                    html.Td(game['teams'][0]),
                    html.Td(
                        dbc.Button(
                            game['spread'][0],
                            id={'type': 'open-modal', 'index': f"{game['teams'][0]}-{i}"},
                            n_clicks=0,
                            color="info"
                        )
                    ),
                    html.Td(game['moneyline'][0]),
                    html.Td(game['total'][0])
                ]),
                html.Tr([
                    html.Td(game['teams'][1]),
                    html.Td(
                        dbc.Button(
                            game['spread'][1],
                            id={'type': 'open-modal', 'index': f"{game['teams'][1]}-{i}"},
                            n_clicks=0,
                            color="info"
                        )
                    ),
                    html.Td(game['moneyline'][1]),
                    html.Td(game['total'][1])
                ])
            ], style={'width': '100%', 'border': '1px solid black', 'text-align': 'center'}),
            # Modals for Each Team's Spread
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(f"{game['teams'][0]} Spread Details")),
                    dbc.ModalBody(id={'type': 'modal-body', 'index': f"{game['teams'][0]}-{i}"})
                ],
                id={'type': 'modal', 'index': f"{game['teams'][0]}-{i}"},
                is_open=False,
                size="xl"
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(f"{game['teams'][1]} Spread Details")),
                    dbc.ModalBody(id={'type': 'modal-body', 'index': f"{game['teams'][1]}-{i}"})
                ],
                id={'type': 'modal', 'index': f"{game['teams'][1]}-{i}"},
                is_open=False,
                size="xl"
            )
        ], style={'margin': '20px', 'border': '1px solid black', 'padding': '20px'})
        for i, game in enumerate(games_data)
    ])
])

# Callback to toggle modals and update modal content
@app.callback(
    [
        Output({'type': 'modal', 'index': MATCH}, 'is_open'),
        Output({'type': 'modal-body', 'index': MATCH}, 'children')
    ],
    Input({'type': 'open-modal', 'index': MATCH}, 'n_clicks'),
    State({'type': 'modal', 'index': MATCH}, 'is_open')
)
def toggle_modal(n_clicks, is_open):
    if n_clicks:
        ctx = dash.callback_context
        if not ctx.triggered:
            return is_open, dash.no_update
        else:
            index = ctx.triggered[0]['prop_id'].split('.')[0]
            index_dict = eval(index)
            modal_index = index_dict['index']  # e.g., 'TeamName-i'

            # Extract team name and game index
            team_name, game_index = modal_index.rsplit('-', 1)
            game_index = int(game_index)

            # Get game data
            game = games_data[game_index]
            game_date = game['game_date']
            game_time = game['time']
            matchup = game['matchup']

            # Clean and standardize strings
            game_date_clean = game_date.replace(' ', '').strip().lower()
            game_time_clean = game_time.strip().lower()
            matchup_clean = matchup.strip().lower()
            team_name_clean = team_name.strip().lower()

            # Clean odds_movements columns
            odds_movements_clean = odds_movements.copy()

            # Filter odds_movements for relevant data
            relevant_odds_movements = odds_movements_clean[
                (odds_movements_clean['game_date'] == game_date_clean) &
                (odds_movements_clean['game_time'] == game_time_clean) &
                (odds_movements_clean['matchup'] == matchup_clean)
            ]

            if not relevant_odds_movements.empty:
                # Ensure columns exist
                available_columns = relevant_odds_movements.columns.tolist()
                columns_to_display = [col for col in ['file1', 'file2', 'sportsbook', 'odds_before', 'odds_after'] if col in available_columns]
                relevant_columns = relevant_odds_movements[columns_to_display]

                # Create table of odds movements
                table_header = [
                    html.Thead(html.Tr([html.Th(col) for col in relevant_columns.columns]))
                ]
                rows = []
                for _, row in relevant_columns.iterrows():
                    rows.append(html.Tr([html.Td(row[col]) for col in relevant_columns.columns]))
                table_body = [html.Tbody(rows)]
                table = dbc.Table(table_header + table_body, bordered=True)
                modal_body = table
            else:
                modal_body = html.P("No odds movement data available for this game.")
            return not is_open, modal_body
    return is_open, dash.no_update

if __name__ == '__main__':
    app.run_server(debug=True)

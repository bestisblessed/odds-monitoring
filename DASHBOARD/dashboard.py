import dash
from dash import dcc, html, Input, Output, State, MATCH
import dash_bootstrap_components as dbc
import pandas as pd
import json
import os
import re

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

def load_odds_movements():
    odds_movements = pd.read_csv('data/nfl_odds_movements.csv')
    odds_movements.loc[:, 'game_date'] = odds_movements['game_date'].str.replace(' ', '').str.strip().str.lower()
    odds_movements.loc[:, 'game_time'] = odds_movements['game_time'].str.replace('\n', ' ').str.replace(r'\s+', ' ', regex=True).str.strip().str.lower()
    odds_movements.loc[:, 'matchup'] = odds_movements['matchup'].str.replace(r'\s+', ' ', regex=True).str.strip().str.lower()
    sportsbooks_to_include = ['Circa', 'Westgate', 'South Point', 'DK']
    filtered_odds = odds_movements[odds_movements['sportsbook'].isin(sportsbooks_to_include)].copy()
    return filtered_odds

odds_movements = load_odds_movements()

def load_games_data():
    games_data = []
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    json_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".json") and f.startswith('nfl')], reverse=True)
    most_recent_file = json_files[0] if json_files else None
    if most_recent_file:
        filepath = os.path.join(data_dir, most_recent_file)
        with open(filepath) as f:
            data = json.load(f)
            for game in data:
                game_time = game['Time']
                day_and_matchup_key = list(game.keys())[1]
                day_and_matchup_value = game[day_and_matchup_key]
                day_and_matchup_column_name = list(game.keys())[1].replace(',', ', ')
                game_date = day_and_matchup_key.strip()
                teams = day_and_matchup_value.replace('\n', ' ').strip()
                teams_list = [team.strip() for team in teams.split('  ')]
                game_date = game_date.replace(' ', '').strip().lower()
                game_time = re.sub(r'\s+', ' ', game_time.replace('\n', ' ')).strip().lower()
                matchup = re.sub(r'\s+', ' ', ' vs '.join(teams_list)).strip().lower()
                circa_spread = game.get("Circa", "").replace('\n', ' ').strip().split(' ')
                if len(circa_spread) == 4:
                    spread_favorite = f"{circa_spread[0]} {circa_spread[1]}"
                    spread_underdog = f"{circa_spread[2]} {circa_spread[3]}"
                else:
                    spread_favorite = "N/A"
                    spread_underdog = "N/A"
                games_data.append({
                    'time': game_time,
                    'day_and_matchup_column_name': day_and_matchup_column_name,
                    'game_date': game_date,
                    'matchup': matchup,
                    'teams': teams_list,
                    'spread': [spread_favorite, spread_underdog],
                    'moneyline': ['N/A', 'N/A'],
                    'total': ['N/A', 'N/A']
                })
    else:
        print("No JSON files found in the data directory.")
    return games_data

games_data = load_games_data()

app.layout = html.Div([
    html.H1("NFL Odds Dashboard", style={'text-align': 'center'}),
    html.Div([
        html.Div([
            html.H3(game['day_and_matchup_column_name']),
            html.H5(game['time'].replace('splits', '').strip()),
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
            modal_index = index_dict['index']
            team_name, game_index = modal_index.rsplit('-', 1)
            game_index = int(game_index)
            game = games_data[game_index]
            game_date = game['game_date']
            game_time = game['time']
            matchup = game['matchup']
            game_date_clean = game_date.replace(' ', '').strip().lower()
            game_time_clean = game_time.strip().lower()
            matchup_clean = matchup.strip().lower()
            team_name_clean = team_name.strip().lower()
            odds_movements_clean = odds_movements.copy()
            relevant_odds_movements = odds_movements_clean.loc[
                (odds_movements_clean['game_date'] == game_date_clean) &
                (odds_movements_clean['game_time'] == game_time_clean) &
                (odds_movements_clean['matchup'] == matchup_clean)
            ].copy()
            if not relevant_odds_movements.empty:
                available_columns = relevant_odds_movements.columns.tolist()
                if 'file2' in available_columns:
                    relevant_odds_movements['timestamp'] = relevant_odds_movements['file2'].apply(
                        lambda x: '_'.join(x.split('_')[3:5]).replace('.json', '')
                    )
                    relevant_odds_movements.loc[:, 'timestamp'] = pd.to_datetime(relevant_odds_movements['timestamp'], format='%Y%m%d_%H%M').dt.strftime('%-m/%d %-I:%M%p').str.lower()
                    available_columns.append('timestamp')
                columns_to_display = [col for col in ['timestamp', 'sportsbook', 'odds_before', 'odds_after'] if col in available_columns]
                relevant_columns = relevant_odds_movements[columns_to_display]
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

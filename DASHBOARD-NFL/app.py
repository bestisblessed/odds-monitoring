from flask import Flask, render_template, jsonify
import os
import json

app = Flask(__name__)

# Function to load all game odds from JSON files
def load_odds_data():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
    # files = sorted([f for f in os.listdir(data_dir) if f.endswith('.json')])
    files = sorted([f for f in os.listdir(data_dir) if f.endswith('.json') and f.startswith('nfl')])
    
    all_odds = {}
    
    for file in files:
        with open(os.path.join(data_dir, file)) as f:
            odds_data = json.load(f)
            timestamp = file.split('_')[2] + "_" + file.split('_')[3].split('.')[0]
            all_odds[timestamp] = odds_data
    
    return all_odds

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/odds')
def get_odds():
    odds_data = load_odds_data()
    return jsonify(odds_data)

if __name__ == '__main__':
    app.run(debug=True)

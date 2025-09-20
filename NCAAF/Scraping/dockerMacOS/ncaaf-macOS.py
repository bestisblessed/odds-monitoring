from playwright.sync_api import sync_playwright
import json
import datetime
import os
import re
import pandas as pd
from datetime import datetime

def format_team_matchup(teams):
    """Format team names into a proper matchup string"""
    if len(teams) == 1:
        return teams[0]
    elif len(teams) == 2:
        return f"{teams[0]} vs {teams[1]}"
    else:
        return " vs ".join(teams)

def extract_odds_from_sportsbook(sportsbook_data):
    """Extract odds information from sportsbook data"""
    if not sportsbook_data:
        return ""
    
    spread = sportsbook_data.get('spread', '')
    odds = sportsbook_data.get('odds', '')
    
    if spread and odds:
        return f"{spread} ({odds})"
    elif spread:
        return spread
    elif odds:
        return odds
    else:
        return ""

def convert_to_csv(data, odds_type, timestamp):
    """Convert JSON data to CSV format"""
    csv_data = []
    
    for game in data:
        # Format team matchup
        matchup = format_team_matchup(game['teams'])
        
        # Create row data
        row = {'Matchup': matchup}
        
        # Add odds for each sportsbook
        odds_data = game.get('odds', {})
        for sportsbook, odds_info in odds_data.items():
            row[sportsbook] = extract_odds_from_sportsbook(odds_info)
        
        csv_data.append(row)
    
    # Convert to DataFrame
    df = pd.DataFrame(csv_data)
    
    # Save to CSV
    csv_filename = os.path.join(script_dir, 'data', f'ncaaf_{odds_type}_{timestamp}.csv')
    df.to_csv(csv_filename, index=False)
    
    print(f"✅ CSV saved: {csv_filename}")
    return csv_filename

# URLs for both spreads and totals
urls = {
    'spreads': 'https://data.vsin.com/college-football/vegas-odds-linetracker/',
    'totals': 'https://data.vsin.com/college-football/vegas-odds-linetracker/?linetype=total&lineperiod=fg'
}

timestamp = datetime.now().strftime("%Y%m%d_%H%M")
script_dir = os.path.dirname(os.path.abspath(__file__))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    for odds_type, url in urls.items():
        print(f"Scraping {odds_type} data from {url}")
        
        try:
            page.goto(url)
            
            # Use Playwright's XPath syntax (xpath= prefix)
            table_xpath = 'xpath=/html/body/div[6]/div[2]/div/div[3]/div/div/div/div[2]/b/div[2]/table'
            page.wait_for_selector(table_xpath, timeout=20000)
            
            # Find the table using Playwright's XPath syntax
            table = page.locator(table_xpath)
            
            # Get table headers
            headers = table.locator('thead th').all_text_contents()
            column_names = [header.strip() for header in headers]
            column_names = [name if name else f"Column{index+1}" for index, name in enumerate(column_names)]
            
            # Get table rows - use all rows (including header)
            all_rows = table.locator('tr')
            data = []
            
            # Process data rows (skip header row)
            for i in range(1, all_rows.count()):
                row = all_rows.nth(i)
                cells = row.locator('td, th').all_text_contents()
                cell_data = [cell.strip() for cell in cells]
                
                if cell_data and len(cell_data) >= 12:  # Ensure we have the expected 12 columns
                    # Extract team names from the second cell (index 1)
                    team_cell = cell_data[1] if len(cell_data) > 1 else ""
                    teams = []
                    if team_cell:
                        team_lines = team_cell.split('\n')
                        teams = [line.strip() for line in team_lines if line.strip() and re.search(r'[A-Z][a-z]', line.strip())]
                    
                    # Extract odds data from sportsbook columns (columns 2-11)
                    odds_data = {}
                    sportsbooks = ['DK Open', 'DK', 'Circa', 'South Point', 'GLD Nugget', 'Westgate', 'Wynn', 'Stations', 'Caesars', 'BetMGM']
                    
                    for j in range(2, min(12, len(cell_data))):
                        if cell_data[j]:
                            odds_text = cell_data[j]
                            # Look for patterns like "+10\n-112" or "-13.5\n-110"
                            odds_match = re.search(r'([+-]?\d+\.?\d*)\s*([+-]?\d+)', odds_text)
                            if odds_match:
                                sportsbook_name = sportsbooks[j-2] if j-2 < len(sportsbooks) else f"Sportsbook{j-2}"
                                odds_data[sportsbook_name] = {
                                    'spread': odds_match.group(1),
                                    'odds': odds_match.group(2)
                                }
                    
                    # Create structured data entry
                    if teams and odds_data:
                        game_data = {
                            'teams': teams,
                            'odds': odds_data,
                            'raw_data': cell_data  # Keep raw data for debugging
                        }
                        data.append(game_data)
            
            # Save data for this odds type
            filename = os.path.join(script_dir, 'data', f'ncaaf_odds_vsin_{odds_type}_{timestamp}.json')
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)
            
            print(f"{odds_type.capitalize()} data has been saved to {filename}")
            print(f"Scraped {len(data)} rows of {odds_type} data")
            
            # Convert to CSV format
            csv_filename = convert_to_csv(data, odds_type, timestamp)
            print(f"CSV format: {csv_filename}")
            
        except Exception as e:
            print(f"An error occurred while scraping {odds_type}: {e}")
    
    browser.close()

print("Scraping completed for both spreads and totals")

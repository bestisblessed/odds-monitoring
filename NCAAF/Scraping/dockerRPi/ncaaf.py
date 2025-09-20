from playwright.sync_api import sync_playwright
import json
import datetime
import os
from datetime import datetime

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
            page.wait_for_selector('table', timeout=20000)
            
            # Find the table
            table = page.locator('table').first
            
            # Get table headers
            headers = table.locator('thead th').all_text_contents()
            column_names = [header.strip() for header in headers]
            column_names = [name if name else f"Column{index+1}" for index, name in enumerate(column_names)]
            
            # Get table rows
            rows = table.locator('tbody tr')
            data = []
            
            for i in range(rows.count()):
                row = rows.nth(i)
                cells = row.locator('td').all_text_contents()
                cell_data = [cell.strip() for cell in cells]
                
                if cell_data:
                    if len(cell_data) != len(column_names):
                        max_length = max(len(cell_data), len(column_names))
                        cell_data.extend([None] * (max_length - len(cell_data)))
                        column_names.extend([f"ExtraColumn{index+1}" for index in range(len(column_names), max_length)])
                    
                    row_data = {column_names[index]: value for index, value in enumerate(cell_data)}
                    data.append(row_data)
            
            # Save data for this odds type
            filename = os.path.join(script_dir, 'data', f'ncaaf_odds_vsin_{odds_type}_{timestamp}.json')
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)
            
            print(f"{odds_type.capitalize()} data has been saved to {filename}")
            print(f"Scraped {len(data)} rows of {odds_type} data")
            
        except Exception as e:
            print(f"An error occurred while scraping {odds_type}: {e}")
    
    browser.close()

print("Scraping completed for both spreads and totals")
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import datetime
import csv
import os
from datetime import datetime
import subprocess
import re

# Try to find chromedriver, with fallback for Docker environment
try:
    chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
except subprocess.CalledProcessError:
    # Fallback for Docker environment where chromedriver is installed via apt
    chromedriver_path = '/usr/bin/chromedriver'
    if not os.path.exists(chromedriver_path):
        raise RuntimeError("ChromeDriver not found. Please ensure it is installed and in your PATH.")

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")  # Required for running on Raspberry Pi
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration for Pi
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-background-timer-throttling")
chrome_options.add_argument("--disable-backgrounding-occluded-windows")
chrome_options.add_argument("--disable-renderer-backgrounding")
# chrome_options.add_argument("--disable-web-security")
# chrome_options.add_argument("--disable-features=VizDisplayCompositor")
# chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_argument("--user-data-dir=/tmp/chrome-temp")
chrome_options.add_experimental_option("prefs", {
    "profile.default_content_settings.popups": 0,
    "download.default_directory": "/tmp",
    "download.prompt_for_download": False
})

service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# URLs for both spreads and totals
urls = {
    'spreads': 'https://data.vsin.com/college-football/vegas-odds-linetracker/',
    'totals': 'https://data.vsin.com/college-football/vegas-odds-linetracker/?linetype=total&lineperiod=fg'
}

timestamp = datetime.now().strftime("%Y%m%d_%H%M")
script_dir = os.path.dirname(os.path.abspath(__file__))

for odds_type, url in urls.items():
    print(f"Scraping {odds_type} data from {url}")
    
    try:
        driver.get(url)
        
        # Wait for page to load completely
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content to load, especially for totals page
        if odds_type == 'totals':
            print("Waiting extra time for totals page to load...")
            import time
            time.sleep(3)  # Initial wait
            
            # Try to refresh the page if it seems to be loading slowly
            try:
                # Check if we have any meaningful data in the first few rows
                test_rows = driver.find_elements(By.TAG_NAME, "tr")[:5]
                has_data = any(cell.text.strip() for row in test_rows for cell in row.find_elements(By.TAG_NAME, "td"))
                
                if not has_data:
                    print("Totals page seems empty, refreshing...")
                    driver.refresh()
                    time.sleep(5)  # Wait after refresh
            except:
                pass
        
        # Try multiple selectors to find the table
        table_selectors = [
            '/html/body/div[6]/div[2]/div/div[3]/div/div/div/div[2]/b/div[2]/table',
            '//table[contains(@class, "odds")]',
            '//table[contains(@class, "line")]',
            '//table[contains(@class, "betting")]',
            '//table'
        ]
        
        table = None
        for selector in table_selectors:
            try:
                table = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                print(f"Found table with selector: {selector}")
                
                # Wait for table to have actual data rows (not just empty cells)
                if odds_type == 'totals':
                    print("Waiting for totals table to populate with data...")
                    import time
                    time.sleep(2)  # Simple wait for data to load
                
                break
            except:
                continue
        
        if not table:
            raise Exception("Could not find any table on the page")

        # Get all rows from the table
        all_rows = table.find_elements(By.TAG_NAME, "tr")
        print(f"Found {len(all_rows)} total rows in table")
        data = []
        
        # Process data rows (skip header row)
        for i in range(1, len(all_rows)):
            row = all_rows[i]
            cells = row.find_elements(By.TAG_NAME, "td")
            cell_data = [cell.text.strip() for cell in cells]
            
            # print(f"Row {i}: {len(cell_data)} columns, data: {cell_data[:3]}...")  # Debug first 3 columns
            
            if cell_data and len(cell_data) >= 3:  # Lower the minimum column requirement for debugging
                # Extract team names from the second cell (index 1)
                team_cell = cell_data[1] if len(cell_data) > 1 else ""
                teams = []
                if team_cell:
                    team_lines = team_cell.split('\n')
                    teams = [line.strip() for line in team_lines if line.strip() and re.search(r'[A-Z][a-z]', line.strip())]
                
                # Extract odds data from sportsbook columns (columns 2 onwards)
                odds_data = {}
                sportsbooks = ['DK Open', 'DK', 'Circa', 'South Point', 'GLD Nugget', 'Westgate', 'Wynn', 'Stations', 'Caesars', 'BetMGM']
                
                for j in range(2, len(cell_data)):
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

    except Exception as e:
        print(f"An error occurred while scraping {odds_type}: {e}")

driver.quit()
print("Scraping completed for both spreads and totals")
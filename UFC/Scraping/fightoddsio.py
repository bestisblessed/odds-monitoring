from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import csv
import json
import os
from datetime import datetime
import subprocess
import pandas as pd
import re

# Find chromedriver path using 'which'
chromedriver_path = "/usr/bin/chromedriver"

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")  # Required for running on Raspberry Pi
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--user-data-dir=/tmp/chrome-temp")
chrome_options.add_experimental_option("prefs", {
    "profile.default_content_settings.popups": 0,
    "download.default_directory": "/tmp",
    "download.prompt_for_download": False
})

# Initialize the Chrome WebDriver with the options and service
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get("https://fightodds.io/")
driver.implicitly_wait(5)

with open("./data/odds_fightoddsio.html", "w", encoding="utf-8") as file:
    file.write(driver.page_source)

driver.quit()

def parse_odds_table(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the main odds table
    table = soup.find('table', {'class': 'MuiTable-root'})
    
    # Get sportsbooks from headers
    headers = []
    for th in table.find('thead').find_all('th'):
        link = th.find('a')
        if link:
            # Extract sportsbook name from href
            sportsbook = link['href'].split('/')[-1]
            headers.append(sportsbook)
        elif not headers:  # Only add Fighters if it's the first column
            headers.append('Fighters')
    
    # Parse rows
    rows = []
    for tr in table.find('tbody').find_all('tr'):
        row_data = []
        
        # Get fighter name
        fighter_link = tr.find('a')
        if fighter_link:
            row_data.append(fighter_link.text)
        
        # Get odds for each sportsbook
        for td in tr.find_all('td')[1:-1]:  # Skip fighter name column and last empty column
            button = td.find('button')
            if button:
                odds_span = button.find('span', {'class': re.compile('jss\\d+ false')})
                if odds_span:
                    row_data.append(odds_span.text)
                else:
                    row_data.append('')
            else:
                row_data.append('')
                
        rows.append(row_data)
    
    # Create DataFrame
    df = pd.DataFrame(rows, columns=headers)
    return df

def save_odds(html_file, output_dir='./data'):
    with open(html_file, 'r') as f:
        html_content = f.read()
    
    # Create timestamp for filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    output_csv = f'{output_dir}/ufc_odds_fightoddsio_{timestamp}.csv'
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    df = parse_odds_table(html_content)
    df.to_csv(output_csv, index=False)
    print(f"Saved odds data to {output_csv}")

if __name__ == "__main__":
    save_odds('./data/odds_fightoddsio.html')

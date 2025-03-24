import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
import subprocess
import pandas as pd
import re

def setup_driver():
    chromedriver_path = "/usr/bin/chromedriver"
    # chromedriver_path = "/opt/homebrew/bin/chromedriver"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-temp")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_settings.popups": 0,
        "download.default_directory": "/tmp",
        "download.prompt_for_download": False
    })
    service = Service(chromedriver_path)
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_vsin():
    driver = setup_driver()
    url = 'https://data.vsin.com/vegas-odds-linetracker/?sportid=ufc&linetype=moneyline'
    driver.get(url)
    data = []
    
    try:
        table_xpath = '/html/body/div[6]/div[2]/div/div[3]/div/div/div/div[2]/b/div[2]/table'
        table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, table_xpath))
        )
        table_children = table.find_elements(By.XPATH, './*')
        column_names = []

        for child in table_children:
            if child.tag_name.lower() == 'thead':
                header_cells = child.find_elements(By.XPATH, './tr/th')
                column_names = [cell.text.strip() if cell.text.strip() else f"Column{index+1}" 
                              for index, cell in enumerate(header_cells)]
            elif child.tag_name.lower() == 'tbody':
                rows = child.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    cell_data = [cell.text.strip() for cell in cells]
                    if cell_data:
                        max_length = max(len(cell_data), len(column_names))
                        cell_data.extend([None] * (max_length - len(cell_data)))
                        column_names.extend([f"ExtraColumn{index+1}" for index in range(len(column_names), max_length)])
                        row_data = {column_names[index]: value for index, value in enumerate(cell_data)}
                        data.append(row_data)
    finally:
        driver.quit()
    
    return data

def parse_odds_table(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'class': 'MuiTable-root'})
    
    headers = []
    for th in table.find('thead').find_all('th'):
        link = th.find('a')
        if link:
            sportsbook = link['href'].split('/')[-1]
            headers.append(sportsbook)
        elif not headers:
            headers.append('Fighters')
    
    rows = []
    for tr in table.find('tbody').find_all('tr'):
        row_data = []
        fighter_link = tr.find('a')
        if fighter_link:
            row_data.append(fighter_link.text)
        
        for td in tr.find_all('td')[1:-1]:
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
    
    return pd.DataFrame(rows, columns=headers)

def scrape_fightodds():
    driver = setup_driver()
    driver.get("https://fightodds.io/")
    driver.implicitly_wait(5)
    
    html_content = driver.page_source
    driver.quit()
    
    return parse_odds_table(html_content)

def save_data(script_dir):
    # Create timestamp and ensure data directory exists
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    data_dir = os.path.join(script_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Save VSIN data
    vsin_data = scrape_vsin()
    vsin_file = os.path.join(data_dir, f'ufc_odds_vsin_{timestamp}.json')
    with open(vsin_file, 'w', encoding='utf-8') as f:
        json.dump(vsin_data, f, ensure_ascii=False, indent=4)
    print(f"VSIN data saved to {vsin_file}")
    
    # Save FightOdds data
    fightodds_data = scrape_fightodds()
    fightodds_file = os.path.join(data_dir, f'ufc_odds_fightoddsio_{timestamp}.csv')
    fightodds_data.to_csv(fightodds_file, index=False)
    print(f"FightOdds data saved to {fightodds_file}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_data(script_dir)


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
import time

def setup_driver():
    chromedriver_path = "/usr/bin/chromedriver"
    #chromedriver_path = "/opt/homebrew/bin/chromedriver"
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

def parse_odds_table(html_content, event_name="Unknown Event"):
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table', {'class': 'MuiTable-root'})
    
    # List to store all fighter data as dictionaries
    all_fighters_data = []
    
    # Set to collect all unique sportsbooks found across all tables
    all_sportsbooks = set()
    
    # First pass: collect all unique sportsbooks from all tables
    for table in tables:
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                link = th.find('a')
                if link and link.get('href'):
                    sportsbook = link['href'].split('/')[-1]
                    all_sportsbooks.add(sportsbook)
    
    # Second pass: process each table and collect fighter data
    for table in tables:
        # Get the sportsbooks from the table header
        sportsbooks = []
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                link = th.find('a')
                if link and link.get('href'):
                    sportsbook = link['href'].split('/')[-1]
                    sportsbooks.append(sportsbook)
        
        # Process table rows
        tbody = table.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                fighter_data = {'Event': event_name}
                
                # Get fighter name
                fighter_link = tr.find('a')
                if fighter_link:
                    fighter_data['Fighters'] = fighter_link.text.strip()
                else:
                    continue  # Skip rows without fighter names
                
                # Get odds for each sportsbook
                odds_cells = tr.find_all('td')[1:-1]  # Skip first (fighter name) and last (empty) cells
                
                for i, td in enumerate(odds_cells):
                    if i < len(sportsbooks):
                        sportsbook = sportsbooks[i]
                        button = td.find('button')
                        if button:
                            odds_span = button.find('span', {'class': re.compile('jss\\d+ false')})
                            if odds_span:
                                fighter_data[sportsbook] = odds_span.text.strip()
                
                all_fighters_data.append(fighter_data)
    
    # Convert to DataFrame
    if all_fighters_data:
        df = pd.DataFrame(all_fighters_data)
        
        # Ensure all fighters have entries for all sportsbooks (even if empty)
        for sportsbook in all_sportsbooks:
            if sportsbook not in df.columns:
                df[sportsbook] = ''
        
        # Ensure Event and Fighters columns are first
        first_cols = ['Event', 'Fighters']
        other_cols = [col for col in df.columns if col not in first_cols]
        df = df[first_cols + other_cols]
        return df
    else:
        # Create an empty DataFrame with the expected columns
        columns = ['Event', 'Fighters'] + list(all_sportsbooks)
        return pd.DataFrame(columns=columns)

def scrape_fightodds():
    driver = setup_driver()
    driver.get("https://fightodds.io/")
    
    # Wait for the main page to load
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "MuiTable-root")))
    
    # Skip scraping the main page data as it duplicates the first event with "MMA Betting Odds" as event name
    all_data = []
    
    # Find all event links based on the HTML structure provided
    # Look for <a> elements that match the structure in the examples
    try:
        # Using a more precise selector based on the provided HTML examples
        event_links = driver.find_elements(By.CSS_SELECTOR, "a.MuiButtonBase-root.MuiListItem-root.MuiListItem-button")
        
        print(f"Found {len(event_links)} event links")
        
        # Print the href and text of each link for debugging
        ufc_event_links = []
        for i, link in enumerate(event_links):
            try:
                href = link.get_attribute('href')
                text = link.text.strip()
                print(f"Link {i}: {text} -> {href}")
                
                # Filter to only include UFC events
                if href and text and ('ufc' in href.lower() or 'ufc' in text.lower()):
                    ufc_event_links.append((link, text, href))
            except:
                print(f"Link {i}: [Could not get details]")
        
        print(f"Found {len(ufc_event_links)} UFC event links")
        
        # Visit each event page and scrape the odds
        for i, (link, event_name, event_url) in enumerate(ufc_event_links):
            try:
                print(f"Navigating to event: {event_name} ({event_url})")
                
                # Open the event page in a new tab
                driver.execute_script(f"window.open('{event_url}', '_blank');")
                
                # Switch to the new tab
                driver.switch_to.window(driver.window_handles[-1])
                
                # Wait for the table to load
                try:
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "MuiTable-root")))
                    time.sleep(2)  # Give extra time for the odds to load
                    
                    # Get the page source and parse it
                    event_html = driver.page_source
                    event_data = parse_odds_table(event_html, event_name)
                    
                    if not event_data.empty:
                        all_data.append(event_data)
                        print(f"Scraped data for {event_name}: {len(event_data)} rows")
                    else:
                        print(f"No data found for {event_name}")
                except Exception as e:
                    print(f"Error loading table for {event_name}: {str(e)}")
                
                # Close the tab and switch back to the main tab
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                
            except Exception as e:
                print(f"Error processing event link {i}: {str(e)}")
                # Make sure we're back on the main tab
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
    
    except Exception as e:
        print(f"Error finding event links: {str(e)}")
    
    driver.quit()
    
    # Combine all the dataframes
    if all_data:
        combined_data = pd.concat(all_data, ignore_index=True)
        return combined_data
    else:
        return pd.DataFrame()

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


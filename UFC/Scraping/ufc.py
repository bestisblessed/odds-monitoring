from datadog import initialize, statsd
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

# --- Datadog setup: no API key needed, agent is local ---
#initialize(statsd_host="localhost", statsd_port=8125)

script_dir = os.path.dirname(os.path.abspath(__file__))
vsin_failed = False
fightodds_failed = False

print("UFC cron script started")

def setup_driver():
    chromedriver_path = "/usr/bin/chromedriver"
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
    all_fighters_data = []
    all_sportsbooks = set()
    for table in tables:
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                link = th.find('a')
                if link and link.get('href'):
                    sportsbook = link['href'].split('/')[-1]
                    all_sportsbooks.add(sportsbook)
    for table in tables:
        sportsbooks = []
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                link = th.find('a')
                if link and link.get('href'):
                    sportsbook = link['href'].split('/')[-1]
                    sportsbooks.append(sportsbook)
        tbody = table.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                fighter_data = {'Event': event_name}
                fighter_link = tr.find('a')
                if fighter_link:
                    fighter_data['Fighters'] = fighter_link.text.strip()
                else:
                    continue
                odds_cells = tr.find_all('td')[1:-1]
                for i, td in enumerate(odds_cells):
                    if i < len(sportsbooks):
                        sportsbook = sportsbooks[i]
                        button = td.find('button')
                        if button:
                            odds_span = button.find('span', {'class': re.compile('jss\\d+ false')})
                            if odds_span:
                                fighter_data[sportsbook] = odds_span.text.strip()
                all_fighters_data.append(fighter_data)
    if all_fighters_data:
        df = pd.DataFrame(all_fighters_data)
        for sportsbook in all_sportsbooks:
            if sportsbook not in df.columns:
                df[sportsbook] = ''
        first_cols = ['Event', 'Fighters']
        other_cols = [col for col in df.columns if col not in first_cols]
        df = df[first_cols + other_cols]
        return df
    else:
        columns = ['Event', 'Fighters'] + list(all_sportsbooks)
        return pd.DataFrame(columns=columns)

def scrape_fightodds():
    driver = setup_driver()
    driver.get("https://fightodds.io/")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "MuiTable-root")))
    all_data = []
    try:
        event_links = driver.find_elements(By.CSS_SELECTOR, "a.MuiButtonBase-root.MuiListItem-root.MuiListItem-button")
        ufc_event_links = []
        for i, link in enumerate(event_links):
            try:
                href = link.get_attribute('href')
                text = link.text.strip()
                if href and text and ('ufc' in href.lower() or 'ufc' in text.lower()):
                    ufc_event_links.append((link, text, href))
            except:
                pass
        for i, (link, event_name, event_url) in enumerate(ufc_event_links):
            try:
                driver.execute_script(f"window.open('{event_url}', '_blank');")
                driver.switch_to.window(driver.window_handles[-1])
                try:
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "MuiTable-root")))
                    time.sleep(2)
                    event_html = driver.page_source
                    event_data = parse_odds_table(event_html, event_name)
                    if not event_data.empty:
                        all_data.append(event_data)
                except Exception:
                    pass
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except Exception:
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
    except Exception:
        pass
    driver.quit()
    if all_data:
        combined_data = pd.concat(all_data, ignore_index=True)
        return combined_data
    else:
        return pd.DataFrame()

# Main execution with independent error handling for both parts
vsin_succeeded = False
fightodds_succeeded = False

try:
    # VSIN
    try:
        vsin_data = scrape_vsin()
        vsin_file = os.path.join(script_dir, 'data', f'ufc_odds_vsin_{datetime.now().strftime("%Y%m%d_%H%M")}.json')
        os.makedirs(os.path.dirname(vsin_file), exist_ok=True)
        with open(vsin_file, 'w', encoding='utf-8') as f:
            json.dump(vsin_data, f, ensure_ascii=False, indent=4)
        vsin_succeeded = True
        print("VSIN data scraped and saved.")
    except Exception:
        print("VSIN scrape failed")
    # FightOdds
    try:
        fightodds_data = scrape_fightodds()
        fightodds_file = os.path.join(script_dir, 'data', f'ufc_odds_fightoddsio_{datetime.now().strftime("%Y%m%d_%H%M")}.csv')
        os.makedirs(os.path.dirname(fightodds_file), exist_ok=True)
        fightodds_data.to_csv(fightodds_file, index=False)
    # Metrics
#    if vsin_succeeded or fightodds_succeeded:
#        statsd.gauge("ufc_odds_monitor.success", 1)
#    else:
#        statsd.gauge("ufc_odds_monitor.failure", 1)
#except Exception:
#    statsd.gauge("ufc_odds_monitor.failure", 1)
#    raise
        fightodds_succeeded = True
        print("FightOdds data scraped and saved.")
    except Exception:
        print("FightOdds scrape failed")
except Exception:
    print("Script execution failed")

print("UFC cron script finished")

os.system("rm -rf /tmp/chrome-temp")
print("Cleaned up temporary Chrome directory")

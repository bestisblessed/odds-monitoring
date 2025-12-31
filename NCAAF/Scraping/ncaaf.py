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
import atexit
from datetime import datetime
import subprocess
import requests
from bs4 import BeautifulSoup

def _build_driver():
    try:
        chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
    except subprocess.CalledProcessError:
        print("ChromeDriver not found. Falling back to HTTP requests.")
        return None

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

    try:
        service = Service(chromedriver_path)
        return webdriver.Chrome(service=service, options=chrome_options)
    except Exception as exc:
        print(f"Failed to start ChromeDriver. Falling back to HTTP requests: {exc}")
        return None


def _cleanup_driver(driver_instance):
    if driver_instance:
        try:
            driver_instance.quit()
        except Exception:
            pass


def _parse_table_rows(column_names, row_cells):
    if not row_cells:
        return None
    if len(row_cells) != len(column_names):
        max_length = max(len(row_cells), len(column_names))
        row_cells.extend([None] * (max_length - len(row_cells)))
        column_names.extend([f"ExtraColumn{index+1}" for index in range(len(column_names), max_length)])
    return {column_names[index]: value for index, value in enumerate(row_cells)}


def _scrape_with_requests(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    if not table:
        raise RuntimeError("No table found in the HTML response.")

    header = table.find("thead")
    column_names = []
    if header:
        header_cells = header.find_all("th")
        column_names = [cell.get_text(strip=True) or f"Column{index+1}" for index, cell in enumerate(header_cells)]

    data = []
    body = table.find("tbody")
    if body:
        for row in body.find_all("tr"):
            cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
            row_data = _parse_table_rows(column_names, cells)
            if row_data:
                data.append(row_data)
    return data

# URLs for both spreads and totals
urls = {
    'spreads': 'https://data.vsin.com/college-football/vegas-odds-linetracker/',
    'totals': 'https://data.vsin.com/college-football/vegas-odds-linetracker/?linetype=total&lineperiod=fg'
}

timestamp = datetime.now().strftime("%Y%m%d_%H%M")
script_dir = os.path.dirname(os.path.abspath(__file__))
driver = _build_driver()
atexit.register(_cleanup_driver, driver)

for odds_type, url in urls.items():
    print(f"Scraping {odds_type} data from {url}")
    
    try:
        if driver:
            driver.get(url)

            table_xpath = '/html/body/div[6]/div[2]/div/div[3]/div/div/div/div[2]/b/div[2]/table'
            table = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )

            table_children = table.find_elements(By.XPATH, './*')
            data = []
            column_names = []

            for child in table_children:
                if child.tag_name.lower() == 'thead':
                    header_cells = child.find_elements(By.XPATH, './tr/th')
                    column_names = [cell.text.strip() for cell in header_cells]
                    column_names = [name if name else f"Column{index+1}" for index, name in enumerate(column_names)]
                elif child.tag_name.lower() == 'tbody':
                    rows = child.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        cell_data = [cell.text.strip() for cell in cells]
                        row_data = _parse_table_rows(column_names, cell_data)
                        if row_data:
                            data.append(row_data)
        else:
            data = _scrape_with_requests(url)

        # Save data for this odds type
        filename = os.path.join(script_dir, 'data', f'ncaaf_odds_vsin_{odds_type}_{timestamp}.json')
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

        print(f"{odds_type.capitalize()} data has been saved to {filename}")
        print(f"Scraped {len(data)} rows of {odds_type} data")

    except Exception as e:
        print(f"An error occurred while scraping {odds_type}: {e}")

if driver:
    driver.quit()
print("Scraping completed for both spreads and totals")

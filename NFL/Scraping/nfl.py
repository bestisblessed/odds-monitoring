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
try:
    chromedriver_path = "/usr/bin/chromedriver"  # Use same path as UFC script
except:
    try:
        chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
    except subprocess.CalledProcessError:
        raise RuntimeError("ChromeDriver not found. Please ensure it is installed and in your PATH.")
chrome_options = Options()
chrome_options.add_argument("--headless")  # Use simple --headless instead of --headless=new
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument(f"--user-data-dir=/tmp/chrome-temp-nfl-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
chrome_options.add_experimental_option("prefs", {
    "profile.default_content_settings.popups": 0,
    "download.default_directory": "/tmp",
    "download.prompt_for_download": False
})
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
url = 'https://data.vsin.com/nfl/vegas-odds-linetracker/'
driver.get(url)
try:
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
                if cell_data:
                    if len(cell_data) != len(column_names):
                        max_length = max(len(cell_data), len(column_names))
                        cell_data.extend([None] * (max_length - len(cell_data)))
                        column_names.extend([f"ExtraColumn{index+1}" for index in range(len(column_names), max_length)])
                    row_data = {column_names[index]: value for index, value in enumerate(cell_data)}
                    data.append(row_data)
        else:
            pass
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    driver.quit()
    # Clean up temporary Chrome directory
    os.system("rm -rf /tmp/chrome-temp-nfl-*")
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
script_dir = os.path.dirname(os.path.abspath(__file__))
filename = os.path.join(script_dir, 'data', 'odds', f'nfl_odds_vsin_{timestamp}.json')
os.makedirs(os.path.dirname(filename), exist_ok=True)
with open(filename, 'w', encoding='utf-8') as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)
print(f"Data has been saved to {filename}")
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
# Try to find chromedriver in common locations
chromedriver_paths = [
    "/usr/bin/chromedriver",  # Linux
    "/opt/homebrew/bin/chromedriver" # Mac with Homebrew
    # "/usr/local/bin/chromedriver",  # Alternative Mac location
]

chromedriver_path = None
for path in chromedriver_paths:
    if os.path.exists(path):
        chromedriver_path = path
        break

# If not found in common locations, try 'which chromedriver'
if chromedriver_path is None:
    try:
        chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
    except subprocess.CalledProcessError:
        raise RuntimeError("ChromeDriver not found. Please ensure it is installed and in your PATH.")

print(f"Using ChromeDriver at: {chromedriver_path}")
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


def _cleanup_driver():
    if driver:
        try:
            driver.quit()
        except Exception:
            pass


atexit.register(_cleanup_driver)
url = 'https://data.vsin.com/nfl/vegas-odds-linetracker/'
print(f"Navigating to: {url}")
driver.get(url)
print("Page loaded, waiting 5 seconds for dynamic content...")
import time
time.sleep(5)  # Give extra time for dynamic content to load

# Debug: Check page title and some basic elements
print(f"Page title: {driver.title}")
print(f"Current URL: {driver.current_url}")

# Check if we can find any tables on the page
all_tables = driver.find_elements(By.TAG_NAME, "table")
print(f"Found {len(all_tables)} tables on the page")

# Debug: Print information about all tables found
for i, table in enumerate(all_tables):
    try:
        table_html = table.get_attribute('outerHTML')[:500]  # First 500 chars
        print(f"Table {i+1}: {table_html}...")
    except Exception as e:
        print(f"Table {i+1}: Could not get HTML - {e}")

    # Try to get XPath for each table
    try:
        xpath = driver.execute_script("""
            function getXPath(element) {
                if (element.id) return '//*[@id="' + element.id + '"]';
                if (element.className) return '//*[' + element.className.split(' ').map(c => 'contains(@class,"' + c + '")').join(' and ') + ']';

                let path = [];
                while (element.nodeType === Node.ELEMENT_NODE) {
                    let selector = element.nodeName.toLowerCase();
                    if (element.id) {
                        selector += '[@id="' + element.id + '"]';
                        path.unshift(selector);
                        break;
                    } else if (element.className) {
                        selector += '[@class="' + element.className + '"]';
                    } else {
                        let sibling = element.previousSibling;
                        let nth = 1;
                        while (sibling) {
                            if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName.toLowerCase() === selector) nth++;
                            sibling = sibling.previousSibling;
                        }
                        if (nth !== 1) selector += '[' + nth + ']';
                    }
                    path.unshift(selector);
                    element = element.parentNode;
                }
                return path.length ? '/' + path.join('/') : '';
            }
            return getXPath(arguments[0]);
        """, table)
        print(f"Table {i+1} XPath: {xpath}")
    except Exception as e:
        print(f"Table {i+1} XPath: Could not determine - {e}")

data = []  # Initialize data before try block
try:
    print("Loading page...")
    # Try multiple possible XPaths for the odds table
    possible_xpaths = [
        '/html/body/div[6]/div[2]/div/div[3]/div/div/div/div[2]/b/div[2]/table',  # Original
        '//table[contains(@class, "odds")]',  # Common odds table class
        '//table[contains(@class, "tracker")]',  # Tracker table
        '//table',  # Just the first table
        '/html/body/div[4]/div[2]/div/div[3]/div/div/div/div[2]/b/div[2]/table',  # Different div numbers
        '/html/body/div[5]/div[2]/div/div[3]/div/div/div/div[2]/b/div[2]/table',  # Different div numbers
    ]

    table = None
    used_xpath = None

    for xpath in possible_xpaths:
        print(f"Trying XPath: {xpath}")
        try:
            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            used_xpath = xpath
            print(f"Table found with XPath: {xpath}")
            break
        except:
            print(f"XPath {xpath} not found, trying next...")
            continue

    if table is None:
        raise Exception("Could not find odds table with any known XPath")

    print(f"Using XPath: {used_xpath}")

    table_children = table.find_elements(By.XPATH, './*')
    print(f"Found {len(table_children)} children in table")

    data = []
    column_names = []
    for child in table_children:
        if child.tag_name.lower() == 'thead':
            header_cells = child.find_elements(By.XPATH, './tr/th')
            column_names = [cell.text.strip() for cell in header_cells]
            column_names = [name if name else f"Column{index+1}" for index, name in enumerate(column_names)]
            print(f"Column names: {column_names}")
        elif child.tag_name.lower() == 'tbody':
            rows = child.find_elements(By.TAG_NAME, "tr")
            print(f"Found {len(rows)} rows in tbody")
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
            print(f"Extracted {len(data)} rows of data")
        else:
            print(f"Skipping child with tag: {child.tag_name}")

    print(f"Total data extracted: {len(data)} rows")

except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()
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
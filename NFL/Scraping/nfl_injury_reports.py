import time
import subprocess
import atexit
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime
import os
try:
    chromedriver_path = "/usr/bin/chromedriver"  # Use same path as UFC script
except:
    try:
        chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
    except subprocess.CalledProcessError:
        raise RuntimeError("ChromeDriver not found. Please ensure it is installed and in your PATH.")
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument(f"--user-data-dir=/tmp/chrome-temp-injury-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
chrome_options.add_experimental_option("prefs", {
    "profile.default_content_settings.popups": 0,
    "download.default_directory": "/tmp",
    "download.prompt_for_download": False
})

service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.set_page_load_timeout(30)


def _cleanup_driver():
    if driver:
        try:
            driver.quit()
        except Exception:
            pass


atexit.register(_cleanup_driver)

try:
    url = 'https://www.espn.com/nfl/injuries'
    try:
        driver.get(url)
    except TimeoutException:
        print("ESPN page load timed out; continuing with the loaded document.")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ResponsiveTable")))
    tables_data = driver.execute_script("""
        return Array.from(document.querySelectorAll('.ResponsiveTable')).map(table => ({
            headers: Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim()),
            rows: Array.from(table.querySelectorAll('tr')).map(row =>
                Array.from(row.querySelectorAll('td')).map(td => td.textContent.trim())
            ).filter(row => row.length)
        }));
    """)
    frames = []
    for table_data in tables_data:
        headers = table_data["headers"]
        rows = [row for row in table_data["rows"] if len(row) == len(headers)]
        if headers and rows:
            frames.append(pd.DataFrame(rows, columns=headers))
    if not frames:
        raise RuntimeError("ESPN injury table contained no data")
    df = pd.concat(frames, ignore_index=True)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "data/injury-reports")
    os.makedirs(output_dir, exist_ok=True)
    today_date = datetime.now().strftime("%Y-%m-%d")
    csv_file_path = os.path.join(output_dir, f"nfl_injury_status_{today_date}.csv")
    df.to_csv(csv_file_path, index=False)
    print(f"Data saved to {csv_file_path}")

finally:
    driver.quit()
    # Clean up temporary Chrome directory
    os.system("rm -rf /tmp/chrome-temp-injury-*")

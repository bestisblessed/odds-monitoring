import time
import subprocess
import atexit
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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

atexit.register(lambda: os.system("pkill chromium"))

service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    url = 'https://www.espn.com/nfl/injuries'
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ResponsiveTable")))
    tables = driver.find_elements(By.CLASS_NAME, "ResponsiveTable")
    all_data = []
    for table in tables:
        headers = [th.text for th in table.find_elements(By.TAG_NAME, "th")]
        rows = table.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            row_data = [td.text for td in row.find_elements(By.TAG_NAME, "td")]
            if row_data:
                all_data.append(row_data)
    df = pd.DataFrame(all_data, columns=headers)
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

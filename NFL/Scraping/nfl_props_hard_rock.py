from bs4 import BeautifulSoup
import csv
import requests
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service  
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import json
import datetime
import os
from datetime import datetime
import time
import pandas as pd
import re
import subprocess

game_id = '2601225827775152149'
url = f'https://app.hardrock.bet/home/competition/nfl/{game_id}'
# https://app.hardrock.bet/home/competition/nfl/2601225827775152149

try:
    chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
except subprocess.CalledProcessError:
    raise RuntimeError("ChromeDriver not found. Please ensure it is installed and in your PATH.")
csv_directory = 'data/props'
os.makedirs(csv_directory, exist_ok=True)
chrome_options = Options()
chrome_options.add_argument("--headless")  
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get(url)
time.sleep(3)
tabs = {
    "Game Lines": "//div[@data-cy='game-details-tab:Game Lines']",
    "Player Props": "//div[@data-cy='game-details-tab:Player Props']",
    "Halves": "//div[@data-cy='game-details-tab:Halves']",
    "Quarters": "//div[@data-cy='game-details-tab:Quarters']"
}
csv_data = []
csv_data.append(["Tab", "Market", "Selection", "Odds"])
for tab_name, tab_xpath in tabs.items():
    tab_element = driver.find_element(By.XPATH, tab_xpath)
    driver.execute_script("arguments[0].click();", tab_element)
    print(f"{tab_name}")  
    time.sleep(3)  
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, "html.parser")
    market_views = soup.find_all("div", class_="marketView")
    for market in market_views:
        header = market.find("div", class_="marketHeader").get_text(strip=True) if market.find("div", class_="marketHeader") else "No Header"
        selections = market.find_all("div", class_="selectionName")
        odds = market.find_all("div", class_="selection-odds")
        for selection, odd in zip(selections, odds):
            selection_name = selection.get_text(strip=True)
            selection_odds = odd.get_text(strip=True)
            csv_data.append([tab_name, header, selection_name, selection_odds])
csv_path = os.path.join(csv_directory, 'hard_rock_nfl_props.csv')  
with open(csv_path, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerows(csv_data)
print(f"All tabs' data has been saved to {csv_path}")
driver.quit()
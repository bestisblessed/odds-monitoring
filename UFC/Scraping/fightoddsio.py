from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import csv
import csv
import json
import os
from datetime import datetime
import subprocess

chromedriver_path = "/usr/bin/chromedriver"

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

service = Service(chromedriver_path)
#driver = webdriver.Chrome(options=chrome_options)
driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get("https://fightodds.io/")

driver.implicitly_wait(5)

with open("./data/odds_fightoddsio.html", "w", encoding="utf-8") as file:
    file.write(driver.page_source)

driver.quit()

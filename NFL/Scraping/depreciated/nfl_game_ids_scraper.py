import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import subprocess
import time
url = 'https://app.hardrock.bet/home/sport-leagues/american_football/691198679103111169'
try:
    chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
except subprocess.CalledProcessError:
    raise RuntimeError("ChromeDriver not found. Please ensure it is installed and in your PATH.")
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get(url)
time.sleep(5)  
html_content = driver.page_source
driver.quit()
soup = BeautifulSoup(html_content, 'html.parser')
numeric_patterns = re.findall(r'\b\d{10,}\b', html_content)
base_url = "https://app.hardrock.bet/home/competition/nfl/"
potential_game_urls = [f"{base_url}{game_id}" for game_id in numeric_patterns]
print("Extracted NFL Game URLs:")
for url in potential_game_urls:
    print(url)


# WORKING LOCAL #
# import re
# from bs4 import BeautifulSoup
# file_path = 'Hard Rock Bet.html'
# with open(file_path, 'r', encoding='utf-8') as file:
#     html_content = file.read()
# soup = BeautifulSoup(html_content, 'html.parser')
# numeric_patterns = re.findall(r'\b\d{10,}\b', html_content)
# base_url = "https://app.hardrock.bet/home/competition/nfl/"
# potential_game_urls = [f"{base_url}{game_id}" for game_id in numeric_patterns]
# print("Extracted NFL Game URLs:")
# for url in potential_game_urls:
#     print(url)
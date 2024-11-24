from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import os
import csv
import subprocess
import pandas as pd

game_id = "490538675"
url = f'https://sports.betonline.ag/sportsbook/football/nfl/game/{game_id}'
# https://sports.betonline.ag/sportsbook/football/nfl/game/490538675

try:
    chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
except subprocess.CalledProcessError:
    raise RuntimeError("ChromeDriver not found. Please ensure it is installed and in your PATH.")
chrome_options = Options()
# chrome_options.add_argument('--headless')  # Make the browser run in headless mode
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get(url)
try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'panel'))
    )
    print("Page is ready!")
except Exception as e:
    print("Loading took too much time or failed!", e)
html_content = driver.page_source
os.makedirs("data/props", exist_ok=True)
with open("data/props/betonline_nfl_props.html", "w", encoding="utf-8") as file:
    file.write(html_content)
print("Saved HTML content for the BetOnline page.")
driver.quit()
html_file_path = 'data/props/betonline_nfl_props.html'
with open(html_file_path, 'r', encoding='utf-8') as file:
    html_content = file.read()
soup = BeautifulSoup(html_content, 'html.parser')
props_data = []
prop_sections = soup.find_all('div', class_='panel')
for section in prop_sections:
    section_title = section.find('div', class_='panel-title')
    if section_title:
        prop_section_name = section_title.get_text(strip=True)
    else:
        prop_section_name = "Unknown Section"
    props_rows = section.find_all('div', class_='picksTable-line')
    for row in props_rows:
        team_name = row.find('p', class_='text-component medium normal twoLinesTruncated left color-primary')
        if team_name:
            team_name = team_name.get_text(strip=True)
            cells = row.find_all('div', class_='picksTable-cell')
            for cell in cells:
                prop_value = cell.get_text(strip=True)
                prop_type = cell.find_previous('p', class_='text-component extra_small normal twoLinesNotTruncated left color-primary')
                if prop_type:
                    prop_type = prop_type.get_text(strip=True)
                else:
                    prop_type = "Unknown Prop"
                props_data.append([team_name, prop_section_name, prop_type, prop_value])
csv_file_path = 'data/props/betonline_nfl_props.csv'
os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Team Name', 'Prop Section', 'Prop Type', 'Value'])  
    writer.writerows(props_data)
df = pd.DataFrame(props_data, columns=['Team Name', 'Prop Section', 'Prop Type', 'Value'])
print(df.head())

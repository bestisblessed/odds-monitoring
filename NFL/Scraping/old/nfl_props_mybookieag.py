from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import os
import csv
import subprocess

game_id = '27015647'  
url = f'https://www.mybookie.ag/sportsbook/nfl/?prop={game_id}'
# https://www.mybookie.ag/sportsbook/nfl/arizona-cardinals/
# https://www.mybookie.ag/sportsbook/nfl/arizona-cardinals/?prop=27015647

try:
    chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
except subprocess.CalledProcessError:
    raise RuntimeError("ChromeDriver not found. Please ensure it is installed and in your PATH.")
chrome_options = Options()
chrome_options.add_argument("--headless")  
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get(url)
time.sleep(5)
html_content = driver.page_source
os.makedirs("data/props", exist_ok=True)
with open("data/props/mybookieag_nfl_props.html", "w", encoding="utf-8") as file:
    file.write(html_content)
print("Saved HTML content for the MyBookie page.")
driver.quit()
soup = BeautifulSoup(html_content, 'html.parser')
game_name_tag = soup.find('p', class_='game-line__banner')
if game_name_tag:
    game_name = game_name_tag.get_text()
else:
    game_name = "Game Name Not Found"
game_time_tag = soup.find('div', class_='sportsbook__line-date')
if game_time_tag:
    game_time = game_time_tag.get_text()
else:
    game_time = "Game Time Not Found"
lines_data = []
props_sections = soup.find_all('div', class_='game-line py-3')
for section in props_sections:
    prop_type_tag = section.find('p', class_='game-line__type__name tnt-name text-right')
    if prop_type_tag:
        prop_type = prop_type_tag.get_text(strip=True)
    else:
        prop_type = "Unknown Prop Type"
    buttons = section.find_all('button', class_='lines-odds')
    for button in buttons:
        lines_data.append([
            button.get('data-description', '').strip(),
            button.get('data-points', '').strip(),
            button.get('data-odd', '').strip(),
            prop_type
        ])
output_file = 'data/props/mybookieag_nfl_props.csv'
with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Description', 'Points', 'Odds', 'Prop Type'])  
    writer.writerows(lines_data)
if os.path.exists("data/props/mybookieag_nfl_props.html"):
    os.remove("data/props/mybookieag_nfl_props.html")
    print("Deleted HTML file.")
print(f"Data has been extracted and saved to {output_file}")

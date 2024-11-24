from bs4 import BeautifulSoup
import pandas as pd
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import re
import subprocess
from datetime import datetime
os.makedirs('data/props', exist_ok=True)
GAME_IDS = {
    'bovada': "arizona-cardinals-seattle-seahawks-202411241625",
    'mybookieag': "27015647", 
    'hard_rock': "2601225827775152149",
    'betonline': "490538675"
}
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
try:
    chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
except subprocess.CalledProcessError:
    raise RuntimeError("ChromeDriver not found. Please ensure it is installed and in your PATH.")
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

### Bovada ###
print("Scraping Bovada...")
bovada_url = f'https://www.bovada.lv/sports/football/nfl/{GAME_IDS["bovada"]}'
bovada_tabs = {
    "Alternate Lines": "//li[@title='Alternate Lines']",
    "TD Scorer Props": "//li[@title='TD Scorer Props']",
    "Passing Props": "//li[@title='Passing Props']",
    "Receiving Props": "//li[@title='Receiving Props']",
    "Rushing Props": "//li[@title='Rushing Props']",
    "D_ST Props": "//li[@title='D/ST Props']",
    "Touchdown Props": "//li[@title='Touchdown Props']",
    "Special Bets": "//li[@title='Special Bets']",
    "Score Props": "//li[@title='Score Props']",
    "Game Props": "//li[@title='Game Props']"
}
driver.get(bovada_url)
time.sleep(4)
for tab_name, tab_xpath in bovada_tabs.items():
    try:
        tab_element = driver.find_element(By.XPATH, tab_xpath)
        driver.execute_script("arguments[0].click();", tab_element)
        time.sleep(4)
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        props_data = []
        if tab_name in ["Passing Props", "Receiving Props", "Rushing Props"]:
            headers = soup.find_all('header', {'class': 'game-heading'})
            for header in headers:
                market_name = header.find('h3', {'class': 'league-header full-width'})
                if not market_name:
                    continue
                market_name = market_name.text.strip()
                match = re.search(r'Total (.+?) - (.+?) \((.+?)\)', market_name)
                if not match:
                    continue
                prop_type, player, team = match.groups()
                market_containers = header.find_all_next('section', {'class': 'coupon-content markets-container'})
                for container in market_containers:
                    line = container.find('ul', {'class': 'spread-header'})
                    line = float(line.find('li').text.strip()) if line and line.find('li') else None
                    odds_spans = container.find_all('span', {'class': 'bet-price'})
                    if odds_spans:
                        over_odds = odds_spans[0].text.strip()
                        under_odds = odds_spans[1].text.strip() if len(odds_spans) > 1 else ''
                        over_odds = int(re.sub(r'[^0-9-]', '', over_odds)) if over_odds and over_odds.replace('-', '').isdigit() else None
                        under_odds = int(re.sub(r'[^0-9-]', '', under_odds)) if under_odds and under_odds.replace('-', '').isdigit() else None
                    else:
                        over_odds = None
                        under_odds = None
                    props_data.append({
                        'Prop_Type': prop_type.strip(),
                        'Player': player.strip(),
                        'Team': team.strip(),
                        'Line': line,
                        'Over_Odds': over_odds,
                        'Under_Odds': under_odds
                    })
        elif tab_name == "Alternate Lines":
            headers = soup.find_all('header', {'class': 'game-heading'})
            for header in headers:
                market_name = header.find('h3', {'class': 'league-header full-width'})
                if not market_name:
                    continue
                market_containers = header.find_next_siblings('section', {'class': 'coupon-content markets-container'})
                for container in market_containers:
                    spread_header = container.find('ul', {'class': 'spread-header'})
                    line = float(spread_header.find('li').text.strip()) if spread_header and spread_header.find('li') else None
                    odds_spans = container.find_all('span', {'class': 'bet-price'})
                    over_odds = int(re.sub(r'[^0-9-]', '', odds_spans[0].text)) if odds_spans else None
                    under_odds = int(re.sub(r'[^0-9-]', '', odds_spans[1].text)) if len(odds_spans) > 1 else None
                    props_data.append({
                        'Market_Name': market_name.text.strip(),
                        'Line': line,
                        'Over_Odds': over_odds,
                        'Under_Odds': under_odds
                    })
        elif tab_name == "D_ST Props":
            for section in soup.find_all("section", class_="coupon-content markets-container"):
                player_header = section.find_previous("h3")
                player_name = player_header.get_text(strip=True) if player_header else None
                spread_header = section.find("ul", class_="spread-header")
                over_value = spread_header.find("li").get_text(strip=True) if spread_header else None
                market_types = section.find_all("ul", class_="market-type")
                if len(market_types) >= 2:
                    over_odds = market_types[0].find("span", class_="bet-price").get_text(strip=True) if market_types[0].find("span", class_="bet-price") else None
                    under_odds = market_types[1].find("span", class_="bet-price").get_text(strip=True) if market_types[1].find("span", class_="bet-price") else None
                    if all([player_name, over_value, over_odds, under_odds]):
                        props_data.append({
                            'Player': player_name,
                            'Over_Value': over_value,
                            'Over_Odds': over_odds,
                            'Under_Odds': under_odds
                        })
        elif tab_name in ["TD Scorer Props", "Touchdown Props"]:
            for outcome in soup.find_all(["button", "sp-outcome"], class_="bet-btn"):
                player_name = outcome.find("span", class_="outcomes")
                odds = outcome.find("span", class_="bet-price")
                if player_name and odds:
                    props_data.append({
                        'Player': player_name.text.strip(),
                        'Odds': odds.text.strip()
                    })
        else:  
            for outcome in soup.find_all(["sp-outcome", "button"], class_=["bet-btn"]):
                description = outcome.find("span", class_="outcomes")
                odds = outcome.find("span", class_="bet-price")
                if description and odds:
                    props_data.append({
                        'Description': description.text.strip(),
                        'Odds': odds.text.strip()
                    })
        if props_data:
            df = pd.DataFrame(props_data)
            df.to_csv(f"data/props/bovada_{tab_name.lower().replace(' ', '_')}_{TIMESTAMP}.csv", index=False)
            print(f"Saved {len(df)} props from {tab_name}")
    except Exception as e:
        print(f"Error processing Bovada {tab_name}: {e}")

### MyBookie ###
print("\nScraping MyBookie...")
mybookie_url = f'https://www.mybookie.ag/sportsbook/nfl/?prop={GAME_IDS["mybookieag"]}'
driver.get(mybookie_url)
time.sleep(5)
html_content = driver.page_source
soup = BeautifulSoup(html_content, 'html.parser')
lines_data = []
game_name_tag = soup.find('p', class_='game-line__banner')
game_name = game_name_tag.get_text() if game_name_tag else "Game Name Not Found"
game_time_tag = soup.find('div', class_='sportsbook__line-date')
game_time = game_time_tag.get_text() if game_time_tag else "Game Time Not Found"
props_sections = soup.find_all('div', class_='game-line py-3')
for section in props_sections:
    prop_type_tag = section.find('p', class_='game-line__type__name tnt-name text-right')
    prop_type = prop_type_tag.get_text(strip=True) if prop_type_tag else "Unknown Prop Type"
    buttons = section.find_all('button', class_='lines-odds')
    for button in buttons:
        lines_data.append([
            button.get('data-description', '').strip(),
            button.get('data-points', '').strip(),
            button.get('data-odd', '').strip(),
            prop_type
        ])
if lines_data:
    df = pd.DataFrame(lines_data, columns=['Description', 'Points', 'Odds', 'Prop Type'])
    df.to_csv(f'data/props/mybookieag_nfl_props_{TIMESTAMP}.csv', index=False)
    print(f"Saved {len(df)} MyBookie props")

### Hard Rock ###
print("\nScraping Hard Rock...")
hard_rock_url = f'https://app.hardrock.bet/home/competition/nfl/{GAME_IDS["hard_rock"]}'
hard_rock_tabs = {
    "Game Lines": "//div[@data-cy='game-details-tab:Game Lines']",
    "Player Props": "//div[@data-cy='game-details-tab:Player Props']",
    "Halves": "//div[@data-cy='game-details-tab:Halves']",
    "Quarters": "//div[@data-cy='game-details-tab:Quarters']"
}
driver.get(hard_rock_url)
time.sleep(3)
all_props_data = []
for tab_name, tab_xpath in hard_rock_tabs.items():
    try:
        tab_element = driver.find_element(By.XPATH, tab_xpath)
        driver.execute_script("arguments[0].click();", tab_element)
        time.sleep(3)
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")
        market_views = soup.find_all("div", class_="marketView")
        for market in market_views:
            header = market.find("div", class_="marketHeader")
            header_text = header.get_text(strip=True) if header else "No Header"
            selections = market.find_all("div", class_="selectionName")
            odds = market.find_all("div", class_="selection-odds")
            for selection, odd in zip(selections, odds):
                selection_name = selection.get_text(strip=True)
                selection_odds = odd.get_text(strip=True)
                all_props_data.append([tab_name, header_text, selection_name, selection_odds])
    except Exception as e:
        print(f"Error processing Hard Rock {tab_name}: {e}")
if all_props_data:
    df = pd.DataFrame(all_props_data, columns=['Tab', 'Market', 'Selection', 'Odds'])
    df.to_csv(f'data/props/hard_rock_nfl_props_{TIMESTAMP}.csv', index=False)
    print(f"Saved {len(df)} Hard Rock props")

### BetOnline ###
print("\nScraping BetOnline...")
betonline_url = f'https://sports.betonline.ag/sportsbook/football/nfl/game/{GAME_IDS["betonline"]}'
driver.get(betonline_url)
try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'panel'))
    )
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, 'html.parser')
    props_data = []
    prop_sections = soup.find_all('div', class_='panel')
    for section in prop_sections:
        section_title = section.find('div', class_='panel-title')
        prop_section_name = section_title.get_text(strip=True) if section_title else "Unknown Section"
        props_rows = section.find_all('div', class_='picksTable-line')
        for row in props_rows:
            team_name = row.find('p', class_='text-component medium normal twoLinesTruncated left color-primary')
            if team_name:
                team_name = team_name.get_text(strip=True)
                cells = row.find_all('div', class_='picksTable-cell')
                for cell in cells:
                    prop_value = cell.get_text(strip=True)
                    prop_type = cell.find_previous('p', class_='text-component extra_small normal twoLinesNotTruncated left color-primary')
                    prop_type = prop_type.get_text(strip=True) if prop_type else "Unknown Prop"
                    props_data.append([team_name, prop_section_name, prop_type, prop_value])
    if props_data:
        df = pd.DataFrame(props_data, columns=['Team Name', 'Prop Section', 'Prop Type', 'Value'])
        df.to_csv(f'data/props/betonline_nfl_props_{TIMESTAMP}.csv', index=False)
        print(f"Saved {len(df)} BetOnline props")
except Exception as e:
    print(f"Error scraping BetOnline: {e}")
finally:
    driver.quit()
    print("\nScraping completed!") 
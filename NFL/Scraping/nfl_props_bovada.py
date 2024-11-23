from bs4 import BeautifulSoup
import pandas as pd
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import os
import time
import re
import subprocess

game_id = "arizona-cardinals-seattle-seahawks-202411241625"
url = f'https://www.bovada.lv/sports/football/nfl/{game_id}'
# https://www.bovada.lv/sports/football/nfl/arizona-cardinals-seattle-seahawks-202411241625

os.makedirs('data/props', exist_ok=True)
try:
    chromedriver_path = subprocess.check_output(['which', 'chromedriver']).strip().decode('utf-8')
except subprocess.CalledProcessError:
    raise RuntimeError("ChromeDriver not found. Please ensure it is installed and in your PATH.")
chrome_options = Options()
chrome_options.add_argument("--headless")
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
tabs = {
    "Alternate Lines": "//li[@title='Alternate Lines']",
    "TD Scorer Props": "//li[@title='TD Scorer Props']",
    "Passing Props": "//li[@title='Passing Props']",
    "Receiving Props": "//li[@title='Receiving Props']",
    "Rushing Props": "//li[@title='Rushing Props']",
    "D_ST Props": "//li[@title='D/ST Props']",
    "Touchdown Props": "//li[@title='Touchdown Props']",
    "Special Bets": "//li[@title='Special Bets']",
    "Parlays": "//li[@title='Parlays']",
    "Score Props": "//li[@title='Score Props']",
    "Game Props": "//li[@title='Game Props']",
    "Correct Score": "//li[@title='Correct Score']"
}
driver.get(url)
time.sleep(4)
for tab_name, tab_xpath in tabs.items():
    try:
        tab_element = driver.find_element(By.XPATH, tab_xpath)
        driver.execute_script("arguments[0].click();", tab_element)
        time.sleep(4)
        html_content = driver.page_source
        html_file_path = f"data/props/bovada_{tab_name.replace(' ', '_')}_tab.html"
        with open(html_file_path, "w", encoding="utf-8") as file:
            file.write(html_content)
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
                        
                        over_odds = int(re.sub(r'[^0-9-]', '', over_odds)) if over_odds and over_odds.isdigit() else None
                        under_odds = int(re.sub(r'[^0-9-]', '', under_odds)) if under_odds and under_odds.isdigit() else None
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
                    over_odds = market_types[0].find("span", class_="bet-price").get_text(strip=True) if market_types[0].find("span", "bet-price") else None
                    under_odds = market_types[1].find("span", "bet-price").get_text(strip=True) if market_types[1].find("span", "bet-price") else None
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
        elif tab_name == "Special Bets":
            for outcome in soup.find_all("sp-outcome"):
                bet_description = outcome.find("span", class_="outcomes")
                bet_odds = outcome.find("span", class_="bet-price")
                if bet_description and bet_odds:
                    props_data.append({
                        'Description': bet_description.text.strip(),
                        'Odds': bet_odds.text.strip()
                    })
        elif tab_name == "Score Props":
            for outcome in soup.find_all("sp-outcome"):
                prop_description = outcome.find("span", class_="outcomes")
                prop_odds = outcome.find("span", class_="bet-price")
                if prop_description and prop_odds:
                    props_data.append({
                        'Description': prop_description.text.strip(),
                        'Odds': prop_odds.text.strip()
                    })
        elif tab_name == "Game Props":
            for outcome in soup.find_all("sp-outcome"):
                prop_description = outcome.find("span", class_="outcomes")
                prop_odds = outcome.find("span", class_="bet-price")
                if prop_description and prop_odds:
                    props_data.append({
                        'Description': prop_description.text.strip(),
                        'Odds': prop_odds.text.strip()
                    })
        elif tab_name == "Correct Score":
            for outcome in soup.find_all("sp-outcome"):
                score_description = outcome.find("span", class_="outcomes")
                score_odds = outcome.find("span", class_="bet-price")
                if score_description and score_odds:
                    props_data.append({
                        'Score': score_description.text.strip(),
                        'Odds': score_odds.text.strip()
                    })
        elif tab_name == "Parlays":
            for outcome in soup.find_all("sp-outcome"):
                parlay_description = outcome.find("span", class_="outcomes")
                parlay_odds = outcome.find("span", class_="bet-price")
                if parlay_description and parlay_odds:
                    props_data.append({
                        'Description': parlay_description.text.strip(),
                        'Odds': parlay_odds.text.strip()
                    })
        else:
            for outcome in soup.find_all(['sp-outcome', 'button'], class_=['bet-btn']):
                description = outcome.find('span', class_='outcomes')
                odds = outcome.find('span', class_='bet-price')
                if description and odds:
                    props_data.append({
                        'Description': description.text.strip(),
                        'Odds': odds.text.strip()
                    })
        if props_data:
            df = pd.DataFrame(props_data)
            csv_path = f"data/props/bovada_{tab_name.replace(' ', '_').lower()}.csv"
            df.to_csv(csv_path, index=False)
            print(f"Saved {len(df)} props from {tab_name} to {csv_path}")
    except Exception as e:
        print(f"Error processing {tab_name}: {e}")
driver.quit()
html_files = [f for f in os.listdir('data/props') if f.endswith('.html')]
for html_file in html_files:
    os.remove(os.path.join('data/props', html_file))
    print(f"Deleted {html_file}")

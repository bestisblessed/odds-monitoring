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
from datetime import datetime, timedelta

os.makedirs('data/props', exist_ok=True)
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

print("🏈 Starting NFL Props Scraper - Dynamic Game Discovery")
print("=" * 60)

# Get Bovada game IDs (cap at 16)
print("Getting Bovada game IDs...")
driver.get("https://www.bovada.lv/sports/football/nfl")
time.sleep(4)

bovada_games = []
bovada_game_data = []
try:
    # Step 1: Get ALL game URLs first (no filtering)
    print("Step 1: Getting ALL Bovada game links...")
    game_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/sports/football/nfl/')]")
    print(f"Found {len(game_links)} total NFL links on page")
    
    # Step 2: Extract all game IDs with any date pattern
    all_games = []
    for link in game_links:
        href = link.get_attribute('href')
        if href and '/sports/football/nfl/' in href:
            game_id = href.split('/sports/football/nfl/')[-1]
            # Accept any game ID that has a date pattern (202X)
            if game_id and re.search(r'202[0-9]', game_id):
                all_games.append({
                    'Game_ID': game_id,
                    'Full_URL': href,
                    'Teams_Date': game_id,
                    'Discovery_Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
    
    # Remove duplicates
    unique_games = {}
    for game in all_games:
        game_id = game['Game_ID']
        if game_id not in unique_games:
            unique_games[game_id] = game
    all_games = list(unique_games.values())
    
    print(f"Step 2: Extracted {len(all_games)} unique game IDs")
    for game in all_games:
        print(f"  Found game: {game['Game_ID']}")
    
    # Step 3: Now filter by date range (6 days from today)
    print("Step 3: Filtering games by date range...")
    today = datetime.now().date()
    cutoff_date = today + timedelta(days=6)
    print(f"Date range: {today} to {cutoff_date}")
    
    filtered_games = []
    for game in all_games:
        try:
            game_id = game['Game_ID']
            # Extract date from game ID (format: team-names-YYYYMMDDHHMM)
            date_match = re.search(r'(\d{12})$', game_id)
            if date_match:
                date_str = date_match.group(1)
                game_date = datetime.strptime(date_str[:8], '%Y%m%d').date()
                
                print(f"  Game: {game_id[:40]}... Date: {game_date}")
                
                if today <= game_date <= cutoff_date:
                    game['Parsed_Date'] = game_date
                    filtered_games.append(game)
                    print(f"    ✅ KEPT (within range)")
                else:
                    print(f"    ❌ FILTERED OUT (outside range)")
            else:
                print(f"  Game: {game_id[:40]}... ❌ No date found in ID")
        except Exception as e:
            print(f"  Error parsing {game_id}: {e}")
    
    # Sort by date (closest first) and take up to 16
    filtered_games.sort(key=lambda x: x.get('Parsed_Date', datetime.max))
    filtered_games = filtered_games[:16]
    
    bovada_games = [game['Game_ID'] for game in filtered_games]
    bovada_game_data = filtered_games
    
    print(f"Step 4: Final result - {len(bovada_games)} games to scrape")
    for game in filtered_games:
        print(f"  Will scrape: {game['Game_ID']} ({game.get('Parsed_Date', 'No date')})")
    
    # Save Bovada game IDs to CSV
    if bovada_game_data:
        df = pd.DataFrame(bovada_game_data)
        filename = f"data/props/bovada_game_ids_{TIMESTAMP}.csv"
        df.to_csv(filename, index=False)
        print(f"💾 Saved {len(bovada_game_data)} Bovada game IDs to {filename}")
    
except Exception as e:
    print(f"Error getting Bovada game IDs: {e}")

# Get MyBookie game IDs (cap at 16)
print("Getting MyBookie game IDs...")
driver.get("https://www.mybookie.ag/sportsbook/nfl/")
time.sleep(5)

mybookie_games = []
mybookie_game_data = []
try:
    more_wager_links = driver.find_elements(By.XPATH, "//a[contains(@href, '?prop=')]")
    for link in more_wager_links:
        href = link.get_attribute('href')
        if '?prop=' in href:
            prop_id = href.split('?prop=')[-1]
            if prop_id.isdigit():
                mybookie_games.append(prop_id)
                
                # Try to get game info from link text or surrounding elements
                link_text = link.text.strip() if link.text else 'More Wagers'
                mybookie_game_data.append({
                    'Game_ID': prop_id,
                    'Full_URL': href,
                    'Link_Text': link_text,
                    'Discovery_Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
    
    mybookie_games = list(set(mybookie_games))[:16]  # Cap at 16 games
    # Also cap the game data to match
    mybookie_game_data = mybookie_game_data[:16]
    print(f"Found {len(mybookie_games)} MyBookie games (capped at 16)")
    
    # Save MyBookie game IDs to CSV
    if mybookie_game_data:
        df = pd.DataFrame(mybookie_game_data)
        filename = f"data/props/mybookie_game_ids_{TIMESTAMP}.csv"
        df.to_csv(filename, index=False)
        print(f"💾 Saved {len(mybookie_game_data)} MyBookie game IDs to {filename}")
    
except Exception as e:
    print(f"Error getting MyBookie game IDs: {e}")

# Get BetOnline game IDs (cap at 16)
print("Getting BetOnline game IDs...")  
driver.get("https://sports.betonline.ag/sportsbook/football/nfl")
time.sleep(5)

betonline_games = []
betonline_game_data = []
try:
    game_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/sportsbook/football/nfl/game/')]")
    for link in game_links:
        href = link.get_attribute('href')
        if '/game/' in href:
            game_id = href.split('/game/')[-1]
            if game_id.isdigit():
                betonline_games.append(game_id)
                
                # Try to get game info from link text
                link_text = link.text.strip() if link.text else 'Game Link'
                betonline_game_data.append({
                    'Game_ID': game_id,
                    'Full_URL': href,
                    'Link_Text': link_text,
                    'Discovery_Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
    
    betonline_games = list(set(betonline_games))[:16]  # Cap at 16 games
    # Also cap the game data to match
    betonline_game_data = betonline_game_data[:16]
    print(f"Found {len(betonline_games)} BetOnline games (capped at 16)")
    
    # Save BetOnline game IDs to CSV
    if betonline_game_data:
        df = pd.DataFrame(betonline_game_data)
        filename = f"data/props/betonline_game_ids_{TIMESTAMP}.csv"
        df.to_csv(filename, index=False)
        print(f"💾 Saved {len(betonline_game_data)} BetOnline game IDs to {filename}")
    
except Exception as e:
    print(f"Error getting BetOnline game IDs: {e}")

print(f"\n📊 DISCOVERED GAMES SUMMARY:")
print(f"Bovada: {len(bovada_games)} games (filtered to ≤6 days)")
print(f"MyBookie: {len(mybookie_games)} games") 
print(f"BetOnline: {len(betonline_games)} games")
print(f"\n💾 Game ID CSV files saved with timestamp: {TIMESTAMP}")
print("=" * 60)

### Bovada ###
if bovada_games:
    print("\n🎯 SCRAPING BOVADA")
    bovada_all_props = []
    
    bovada_tabs = {
        "Passing Props": "//li[@title='Passing Props']",
        "Receiving Props": "//li[@title='Receiving Props']", 
        "Rushing Props": "//li[@title='Rushing Props']",
        "TD Scorer Props": "//li[@title='TD Scorer Props']",
        "Game Props": "//li[@title='Game Props']"
    }
    
    for game_id in bovada_games:
        print(f"Scraping Bovada game: {game_id}")
        bovada_url = f'https://www.bovada.lv/sports/football/nfl/{game_id}'
        
        try:
            driver.get(bovada_url)
            time.sleep(4)
            
            for tab_name, tab_xpath in bovada_tabs.items():
                try:
                    tab_element = driver.find_element(By.XPATH, tab_xpath)
                    driver.execute_script("arguments[0].click();", tab_element)
                    time.sleep(3)
                    
                    html_content = driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
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
                                    
                                bovada_all_props.append({
                                    'Game_ID': game_id,
                                    'Prop_Type': prop_type.strip(),
                                    'Player': player.strip(),
                                    'Team': team.strip(), 
                                    'Line': line,
                                    'Over_Odds': over_odds,
                                    'Under_Odds': under_odds
                                })
                    
                    elif tab_name == "TD Scorer Props":
                        for outcome in soup.find_all(["button", "sp-outcome"], class_="bet-btn"):
                            player_name = outcome.find("span", class_="outcomes")
                            odds = outcome.find("span", class_="bet-price")
                            if player_name and odds:
                                bovada_all_props.append({
                                    'Game_ID': game_id,
                                    'Player': player_name.text.strip(),
                                    'Odds': odds.text.strip()
                                })
                        
                except Exception as e:
                    print(f"Error scraping Bovada {tab_name}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error scraping Bovada game {game_id}: {e}")
        
        time.sleep(2)  # Be respectful
        
    if bovada_all_props:
        df = pd.DataFrame(bovada_all_props)
        filename = f"data/props/bovada_all_games_{TIMESTAMP}.csv"
        df.to_csv(filename, index=False)
        print(f"✅ Saved {len(bovada_all_props)} Bovada props to {filename}")

### MyBookie ###
if mybookie_games:
    print("\n🎯 SCRAPING MYBOOKIE")
    mybookie_all_props = []
    
    for game_id in mybookie_games:
        print(f"Scraping MyBookie game: {game_id}")
        mybookie_url = f'https://www.mybookie.ag/sportsbook/nfl/?prop={game_id}'
        
        try:
            driver.get(mybookie_url)
            time.sleep(5)
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            game_name_tag = soup.find('p', class_='game-line__banner')
            game_name = game_name_tag.get_text() if game_name_tag else "Game Name Not Found"
            
            props_sections = soup.find_all('div', class_='game-line py-3')
            for section in props_sections:
                prop_type_tag = section.find('p', class_='game-line__type__name tnt-name text-right')
                prop_type = prop_type_tag.get_text(strip=True) if prop_type_tag else "Unknown Prop Type"
                
                buttons = section.find_all('button', class_='lines-odds')
                for button in buttons:
                    mybookie_all_props.append({
                        'Game_ID': game_id,
                        'Game_Name': game_name,
                        'Description': button.get('data-description', '').strip(),
                        'Points': button.get('data-points', '').strip(),
                        'Odds': button.get('data-odd', '').strip(),
                        'Prop_Type': prop_type
                    })
            
            print(f"Found {len(props_sections)} MyBookie prop sections for game {game_id}")
            
        except Exception as e:
            print(f"Error scraping MyBookie game {game_id}: {e}")
        
        time.sleep(2)  # Be respectful
        
    if mybookie_all_props:
        df = pd.DataFrame(mybookie_all_props)
        filename = f"data/props/mybookie_all_games_{TIMESTAMP}.csv"
        df.to_csv(filename, index=False)
        print(f"✅ Saved {len(mybookie_all_props)} MyBookie props to {filename}")

### BetOnline ###
if betonline_games:
    print("\n🎯 SCRAPING BETONLINE") 
    betonline_all_props = []
    
    for game_id in betonline_games:
        print(f"Scraping BetOnline game: {game_id}")
        betonline_url = f'https://sports.betonline.ag/sportsbook/football/nfl/game/{game_id}'
        
        try:
            driver.get(betonline_url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'panel'))
            )
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
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
                            
                            betonline_all_props.append({
                                'Game_ID': game_id,
                                'Team_Name': team_name,
                                'Prop_Section': prop_section_name,
                                'Prop_Type': prop_type,
                                'Value': prop_value
                            })
            
            print(f"Found {len(prop_sections)} BetOnline prop sections for game {game_id}")
            
        except Exception as e:
            print(f"Error scraping BetOnline game {game_id}: {e}")
        
        time.sleep(2)  # Be respectful
        
    if betonline_all_props:
        df = pd.DataFrame(betonline_all_props)
        filename = f"data/props/betonline_all_games_{TIMESTAMP}.csv"
        df.to_csv(filename, index=False)
        print(f"✅ Saved {len(betonline_all_props)} BetOnline props to {filename}")

driver.quit()
print("\n🎉 SCRAPING COMPLETED!")
print("=" * 60)

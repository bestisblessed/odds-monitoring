#!/usr/bin/env python3
"""
OddsChecker NFL Props Scraper - Production Version
Includes retry logic and anti-detection measures
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re
from datetime import datetime
import random

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 300  # 5 minutes between retries
MAX_GAMES = 16  # Full week coverage

# Create output directory
os.makedirs('data/props', exist_ok=True)
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

print("🏈 Starting Production OddsChecker NFL Props Scraper")
print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

def create_session():
    """Create a requests session with realistic headers"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    })
    return session

def random_delay(min_seconds=2, max_seconds=5):
    """Human-like random delay"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def extract_prop_data(article, game_name, game_url):
    """Extract prop data with enhanced player and sportsbook detection"""
    data = []
    
    # Determine prop type
    prop_type = "Unknown"
    buttons = article.find_all('button')
    
    for button in buttons:
        text = button.get_text(strip=True)
        if any(keyword in text.lower() for keyword in [
            'spread', 'total', 'moneyline', 'touchdown', 'passing', 
            'rushing', 'receiving', 'yards', 'points', 'tackles', 'attempts'
        ]):
            if not re.match(r'^[+-]\d+$', text):
                prop_type = text
                break
    
    # Enhanced player name extraction
    players = []
    text_elements = article.find_all(string=True)
    for text in text_elements:
        text = text.strip()
        # More comprehensive player name detection
        if (re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?(?:\s(?:Jr|Sr|III|IV))?\.?$', text) and 
            len(text) > 5 and len(text) < 35 and
            not any(skip in text.lower() for skip in [
                'more odds', 'show more', 'compare', 'bet', 'odds', 'over', 'under'
            ])):
            if text not in players:
                players.append(text)
    
    # Remove duplicates and limit
    players = list(dict.fromkeys(players))[:15]
    
    # Enhanced sportsbook detection - look for expanded matrices
    sportsbooks = []
    imgs = article.find_all('img', alt=True)
    for img in imgs:
        alt_text = img.get('alt', '').strip()
        # Known sportsbook patterns
        if any(book in alt_text.lower() for book in [
            'fanduel', 'draftkings', 'betmgm', 'bet365', 'caesars', 
            'borgata', 'betrivers', 'pointsbet', 'foxbet'
        ]):
            if alt_text not in sportsbooks:
                sportsbooks.append(alt_text)
    
    # If multiple sportsbooks found, we likely have a comparison matrix
    if len(sportsbooks) > 1:
        print(f"    🎯 Found comparison matrix: {len(sportsbooks)} sportsbooks")
    
    # Extract odds
    odds_buttons = article.find_all('button')
    odds_values = []
    for button in odds_buttons:
        text = button.get_text(strip=True)
        if re.match(r'^[+-]\d+$', text):
            odds_values.append(text)
    
    # Create data entries with intelligent mapping
    if odds_values:
        if players and sportsbooks and len(odds_values) >= len(players):
            # Matrix structure detected
            odds_per_player = min(len(sportsbooks), len(odds_values) // len(players) if len(players) > 0 else 1)
            
            for i, player in enumerate(players):
                for j in range(odds_per_player):
                    odds_index = i * odds_per_player + j
                    if odds_index < len(odds_values):
                        sportsbook = sportsbooks[j] if j < len(sportsbooks) else sportsbooks[0]
                        data.append({
                            'Game': game_name,
                            'Game_URL': game_url,
                            'Prop_Type': prop_type,
                            'Player': player,
                            'Sportsbook': sportsbook,
                            'Odds': odds_values[odds_index],
                            'Matrix_Detected': True,
                            'Scraped_At': datetime.now().isoformat()
                        })
        else:
            # Fallback: basic structure
            for i, odds in enumerate(odds_values[:10]):
                player = players[i] if i < len(players) else f"Option_{i+1}"
                sportsbook = sportsbooks[0] if sportsbooks else "Primary"
                
                data.append({
                    'Game': game_name,
                    'Game_URL': game_url,
                    'Prop_Type': prop_type,
                    'Player': player,
                    'Sportsbook': sportsbook,
                    'Odds': odds,
                    'Matrix_Detected': False,
                    'Scraped_At': datetime.now().isoformat()
                })
    
    return data

def scrape_with_retries():
    """Main scraping function with retry logic"""
    
    for attempt in range(MAX_RETRIES):
        try:
            session = create_session()
            
            print(f"🔄 Attempt {attempt + 1}/{MAX_RETRIES}")
            
            # Get main page
            print("📥 Fetching main NFL page...")
            response = session.get("https://www.oddschecker.com/us/football/nfl")
            
            if response.status_code == 403:
                print(f"❌ Blocked (403) - Waiting {RETRY_DELAY} seconds before retry...")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    return None
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code} - Retrying...")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            print(f"✅ Main page loaded successfully")
            
            # Try to read game URLs from CSV file first
            game_urls = []
            csv_file = 'data/props/oddschecker_game_urls.csv'
            
            if os.path.exists(csv_file):
                print(f"📁 Reading game URLs from {csv_file}")
                try:
                    df_games = pd.read_csv(csv_file)
                    if 'Game URL' in df_games.columns:
                        game_urls = df_games['Game URL'].tolist()
                        print(f"✅ Loaded {len(game_urls)} games from CSV")
                        for i, url in enumerate(game_urls, 1):
                            print(f"🏈 Game {i}: {url.split('/')[-1].replace('-', ' ').title()}")
                    else:
                        print("❌ 'Game URL' column not found in CSV")
                except Exception as e:
                    print(f"❌ Error reading CSV: {e}")
            
            # Fallback: Extract game URLs from main page if CSV not available
            if not game_urls:
                print("📥 CSV not found, extracting game URLs from main page...")
                team_links = soup.find_all('a', href=re.compile(r'/us/football/nfl/.*-at-.*'))
                
                for link in team_links:
                    href = link.get('href')
                    if href and '/us/football/nfl/' in href and '-at-' in href:
                        if any(word in href for word in ['super-bowl', 'afc/', 'nfc/', 'winner', 'seed']):
                            continue
                        
                        if href.startswith('/'):
                            href = 'https://www.oddschecker.com' + href
                        
                        if href not in game_urls:
                            game_urls.append(href)
                            print(f"🏈 Game {len(game_urls)}: {href.split('/')[-1].replace('-', ' ').title()}")
                        
                        if len(game_urls) >= MAX_GAMES:
                            break
            
            print(f"📋 Found {len(game_urls)} games to scrape")
            
            # Scrape each game
            all_data = []
            
            for game_num, game_url in enumerate(game_urls, 1):
                print(f"\n🎯 Scraping game {game_num}/{len(game_urls)}")
                print(f"   URL: {game_url}")
                
                random_delay(3, 6)  # Respectful delay
                
                try:
                    game_response = session.get(game_url)
                    if game_response.status_code == 200:
                        game_soup = BeautifulSoup(game_response.content, 'html.parser')
                        game_name = game_url.split('/')[-1].replace('-', ' ').title()
                        
                        articles = game_soup.find_all('article')
                        game_data = []
                        
                        for article in articles:
                            article_data = extract_prop_data(article, game_name, game_url)
                            game_data.extend(article_data)
                        
                        all_data.extend(game_data)
                        print(f"   ✅ Extracted {len(game_data)} odds")
                        
                    else:
                        print(f"   ❌ Game page failed: {game_response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Game scraping error: {e}")
                    continue
            
            return all_data
            
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"⏳ Waiting {RETRY_DELAY} seconds before retry...")
                time.sleep(RETRY_DELAY)
    
    return None

# Run the scraper
if __name__ == "__main__":
    data = scrape_with_retries()
    
    if data:
        df = pd.DataFrame(data)
        filename = f"data/props/oddschecker_production_nfl_props_{TIMESTAMP}.csv"
        df.to_csv(filename, index=False)
        
        print("\n" + "=" * 60)
        print("🎉 PRODUCTION SCRAPING COMPLETED!")
        print("=" * 60)
        print(f"✅ Total odds scraped: {len(data)}")
        print(f"✅ Unique games: {df['Game'].nunique()}")
        print(f"✅ Unique prop types: {df['Prop_Type'].nunique()}")
        print(f"✅ Unique players: {df['Player'].nunique()}")
        print(f"✅ Unique sportsbooks: {df['Sportsbook'].nunique()}")
        
        # Matrix detection summary
        matrix_count = len(df[df['Matrix_Detected'] == True]) if 'Matrix_Detected' in df.columns else 0
        print(f"✅ Matrix odds detected: {matrix_count}")
        
        print(f"✅ Saved to: {filename}")
        
        # Show sportsbook breakdown
        if len(df['Sportsbook'].unique()) > 1:
            print("\n📊 Sportsbooks found:")
            for book, count in df['Sportsbook'].value_counts().items():
                print(f"  {book}: {count} odds")
        
        print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    else:
        print("\n❌ All scraping attempts failed")
        print("💡 Try running at a different time (early morning/late night)")
        print("💡 Consider using VPN or proxy rotation")
    
    print("\n🏁 Scraper finished!")

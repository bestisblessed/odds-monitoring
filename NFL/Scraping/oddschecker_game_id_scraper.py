import re, pandas as pd
import requests
from bs4 import BeautifulSoup
import os

# Create output directory
os.makedirs('data/props', exist_ok=True)

URL = "https://www.oddschecker.com/us/football/nfl"

# Setup requests session with realistic headers
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    # 'Accept-Language': 'en-US,en;q=0.9',
    # 'Accept-Encoding': 'gzip, deflate, br',
    # 'DNT': '1',
    # 'Connection': 'keep-alive',
    # 'Upgrade-Insecure-Requests': '1',
    # 'Sec-Fetch-Dest': 'document',
    # 'Sec-Fetch-Mode': 'navigate',
    # 'Sec-Fetch-Site': 'none',
    # 'Sec-Fetch-User': '?1',
    # 'Cache-Control': 'max-age=0'
})

response = session.get(URL)
print(f"Response status: {response.status_code}")

if response.status_code == 200:
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try multiple approaches to find game URLs
    game_urls = []
    
    # Method 1: Look for href attributes with game patterns
    team_links = soup.find_all('a', href=re.compile(r'/us/football/nfl/.*-at-.*'))
    
    for link in team_links:
        href = link.get('href')
        if href and '/us/football/nfl/' in href and '-at-' in href:
            # Skip futures/season pages
            if any(word in href for word in ['super-bowl', 'afc/', 'nfc/', 'winner', 'seed']):
                continue
            
            # Make sure it's a full URL
            if href.startswith('/'):
                href = 'https://www.oddschecker.com' + href
            
            if href not in game_urls:
                game_urls.append(href)
    
    # Method 2: Regex pattern on HTML content
    pattern = re.compile(r'"urlPath":"(/us/football/nfl/[^"/]+-at-[^"/]+)"')
    paths = pattern.findall(html)
    
    for p in paths:
        full_url = "https://www.oddschecker.com" + p
        if full_url not in game_urls:
            game_urls.append(full_url)
    
    # Method 3: Look for JSON data or script tags
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            # Look for game URLs in script content
            script_urls = re.findall(r'/us/football/nfl/[^"\']+?-at-[^"\']+', script.string)
            for url in script_urls:
                if not any(word in url for word in ['super-bowl', 'afc/', 'nfc/', 'winner', 'seed']):
                    full_url = "https://www.oddschecker.com" + url
                    if full_url not in game_urls:
                        game_urls.append(full_url)

    out = "data/props/oddschecker_game_urls.csv"
    pd.DataFrame({"Game URL": game_urls[:16]}).to_csv(out, index=False)

    print(f"Found {len(game_urls)} unique base game URLs; saved first 16 to {out}")
    if game_urls:
        print(*game_urls[:16], sep="\n")
    else:
        print("No game URLs found. The page structure may have changed.")
        # Debug: save HTML content for inspection
        with open("debug_oddschecker.html", "w") as f:
            f.write(html)
        print("Saved HTML content to debug_oddschecker.html for inspection")
else:
    print(f"Failed to fetch page: {response.status_code}")

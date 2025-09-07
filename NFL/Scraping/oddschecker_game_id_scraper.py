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
    # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    # 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    # 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    # 'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    # 'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0',
    # 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    # 'User-Agent': 'Mozilla/5.0 (Linux; Android 9; SM-T510) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    
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
    
    # -----------------------------
    # Extract kickoff times from embedded JSON
    # We match urlPath and startTime pairs, allowing either order.
    # -----------------------------
    pair_pat = re.compile(
        r'"urlPath"\s*:\s*"(/us/football/nfl/[^"/]+-at-[^"/]+)".*?"startTime"\s*:\s*"([^"]+)"'
        r'|'
        r'"startTime"\s*:\s*"([^"]+)".*?"urlPath"\s*:\s*"(/us/football/nfl/[^"/]+-at-[^"/]+)"',
        re.S,
    )
    kickoff_by_path = {}
    for m in pair_pat.finditer(html):
        # path/time regardless of which side matched
        path = m.group(1) or m.group(4)
        tiso = m.group(2) or m.group(3)
        if path and path not in kickoff_by_path:
            kickoff_by_path[path] = tiso  # ISO8601, typically in Z (UTC)
    
    # Try multiple approaches to find game URLs
    game_urls = []
    seen = set()
    
    # Method 1: Look for href attributes with game patterns
    team_links = soup.find_all('a', href=re.compile(r'/us/football/nfl/.*-at-.*'))
    
    for link in team_links:
        href = link.get('href')
        if not href:
            continue
        if '/us/football/nfl/' in href and '-at-' in href:
            # Skip futures/season pages
            if any(word in href for word in ['super-bowl', 'afc/', 'nfc/', 'winner', 'seed']):
                continue
            if href.startswith('/'):
                href = 'https://www.oddschecker.com' + href
            if href not in seen:
                seen.add(href)
                game_urls.append(href)
    
    # Method 2: Regex pattern on HTML content for urlPath
    for p in re.findall(r'"urlPath":"(/us/football/nfl/[^"/]+-at-[^"/]+)"', html):
        full_url = "https://www.oddschecker.com" + p
        if full_url not in seen:
            seen.add(full_url)
            game_urls.append(full_url)
    
    # Method 3: Look for URLs inside inline scripts
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            for url in re.findall(r'/us/football/nfl/[^"\']+?-at-[^"\']+', script.string):
                if any(word in url for word in ['super-bowl', 'afc/', 'nfc/', 'winner', 'seed']):
                    continue
                full_url = "https://www.oddschecker.com" + url if url.startswith('/') else url
                if full_url not in seen:
                    seen.add(full_url)
                    game_urls.append(full_url)

    # Build rows + add kickoff columns (EST only)
    rows = []
    for full_url in game_urls[:16]:
        # derive path to look up kickoff
        path = full_url.replace("https://www.oddschecker.com", '') if full_url.startswith("https://www.oddschecker.com") else full_url
        tiso = kickoff_by_path.get(path)
        
        # Convert UTC to EST directly
        kickoff_est = ''
        if tiso:
            try:
                dt = pd.to_datetime(tiso, utc=True)
                kickoff_est = dt.tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M:%S %Z')
            except:
                kickoff_est = ''
        
        rows.append({
            'Game URL': full_url,
            'Kickoff EST': kickoff_est
        })

    df = pd.DataFrame(rows)
    out = "data/props/oddschecker_game_urls.csv"
    df.to_csv(out, index=False)

    print(f"Found {len(game_urls)} unique base game URLs; saved first 16 with dates to {out}")
    print(df.to_string(index=False))

    if not game_urls:
        print("No game URLs found. The page structure may have changed.")
        # Debug: save HTML content for inspection
        with open("debug_oddschecker.html", "w") as f:
            f.write(html)
        print("Saved HTML content to debug_oddschecker.html for inspection")
else:
    print(f"Failed to fetch page: {response.status_code}")

from datadog import initialize, statsd
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import csv
import os
import atexit
from datetime import datetime
import subprocess
import pandas as pd
import re
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
print("UFC Totals scraper started")

def clean_event_name(name: str) -> str:
    """Normalize event names by collapsing whitespace and removing trailing lone numbers."""
    if not isinstance(name, str):
        return str(name)
    cleaned = re.sub(r"\s+", " ", name).strip()
    cleaned = re.sub(r"\s+\d{1,3}$", "", cleaned)
    return cleaned

def is_combination_prop(totals_type: str) -> bool:
    """Check if totals_type is a combination prop (fighter name + over/under)."""
    if not totals_type:
        return False
    totals_lower = totals_type.lower()
    # Combination props contain patterns like:
    # - "wins and" + over/under
    # - "doesn't win or" + over/under
    # - "doesn't win and" + over/under
    # - "wins or" + over/under
    has_win_condition = re.search(r'\b(wins|win)\s+(and|or)\b', totals_lower) or \
                       re.search(r"\bdoesn'?t\s+win\s+(and|or)\b", totals_lower)
    has_over_under = re.search(r'\b(over|under)\s+\d+\.?\d*\s+rounds?\b', totals_lower)
    return bool(has_win_condition and has_over_under)

def register_driver_cleanup(driver):
    def _cleanup():
        try:
            driver.quit()
        except Exception:
            pass
    atexit.register(_cleanup)

# in setup_driver() of ufc_totals.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-temp")
    chrome_options.binary_location = "/usr/bin/chromium"       # Raspberry Pi chromium
    service = Service(executable_path="/usr/bin/chromedriver") # Raspberry Pi chromedriver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)
    return driver

def parse_totals_table(html_content, event_name="Unknown Event"):
    """Parse Over/Under totals from the odds table."""
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table', {'class': 'MuiTable-root'})
    all_totals_data = []
    all_sportsbooks = set()
    # Track the current fight pairing as we traverse rows
    last_fighter_name = None
    current_fighter_1 = None
    current_fighter_2 = None
    
    # First pass: collect all sportsbooks
    for table in tables:
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                link = th.find('a')
                if link and link.get('href'):
                    sportsbook = link['href'].split('/')[-1]
                    all_sportsbooks.add(sportsbook)
    
    # Second pass: extract totals data
    for table in tables:
        sportsbooks = []
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                link = th.find('a')
                if link and link.get('href'):
                    sportsbook = link['href'].split('/')[-1]
                    sportsbooks.append(sportsbook)
        
        tbody = table.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                first_cell = tr.find('td')
                if not first_cell:
                    continue
                
                # Detect fighter rows and maintain the current pairing context
                fighter_link = first_cell.find('a', href=True)
                if fighter_link and '/fighters/' in fighter_link.get('href', ''):
                    fighter_name = fighter_link.get_text(strip=True)
                    if not last_fighter_name:
                        last_fighter_name = fighter_name
                    else:
                        current_fighter_1 = last_fighter_name
                        current_fighter_2 = fighter_name
                        last_fighter_name = None
                    # Skip to next row; fighter rows are not totals rows
                    continue
                
                first_cell_text = first_cell.get_text(strip=True)
                
                # Check if this is an Over/Under totals row
                # Totals can appear as:
                # 1. Text like "Over 1.5 rounds" in first cell
                # 2. Empty first cell with rowspan and odds in subsequent cells (user's HTML example)
                is_totals_row = False
                totals_type = None
                
                # Pattern 1: Explicit totals text
                if re.search(r'(?i)(over|under)\s+\d+\.?\d*\s+rounds?', first_cell_text):
                    is_totals_row = True
                    totals_type = first_cell_text
                elif re.search(r'(?i)fight\s+goes\s+the\s+distance', first_cell_text):
                    is_totals_row = True
                    totals_type = first_cell_text
                # Pattern 2: Check if any cell in the row contains totals text (not just first cell)
                if not is_totals_row:
                    all_cells = tr.find_all('td')
                    for cell in all_cells:
                        cell_text = cell.get_text(strip=True)
                        if re.search(r'(?i)(over|under)\s+\d+\.?\d*\s+rounds?', cell_text):
                            is_totals_row = True
                            totals_type = cell_text
                            break
                        elif re.search(r'(?i)fight\s+goes\s+the\s+distance', cell_text):
                            is_totals_row = True
                            totals_type = cell_text
                            break
                
                if is_totals_row:
                    # Filter out combination props (fighter name + over/under)
                    if is_combination_prop(totals_type):
                        continue
                    
                    totals_data = {
                        'Event': clean_event_name(event_name),
                        'Fighter1': current_fighter_1 or '',
                        'Fighter2': current_fighter_2 or '',
                        'Totals_Type': totals_type
                    }
                    
                    # Extract odds from all cells (skip first and last)
                    odds_cells = tr.find_all('td')[1:-1]
                    for i, td in enumerate(odds_cells):
                        if i < len(sportsbooks):
                            sportsbook = sportsbooks[i]
                            
                            # Try multiple methods to extract odds
                            odds_value = None
                            
                            # Method 1: Button with span (standard pattern)
                            button = td.find('button')
                            if button:
                                odds_span = None
                                # Pattern 1: jss\d+ false (UFC/PFL style)
                                odds_span = button.find('span', {'class': re.compile('jss\\d+ false')})
                                # Pattern 2: jss\d+ (ONE Championship style)
                                if not odds_span:
                                    all_spans = button.find_all('span')
                                    for span in all_spans:
                                        span_classes = span.get('class', [])
                                        if span_classes and any(re.match(r'jss\d+', str(c)) for c in span_classes):
                                            text = span.text.strip()
                                            if text and re.match(r'^[+-]?\d+$', text):
                                                odds_span = span
                                                break
                                if odds_span:
                                    odds_value = odds_span.text.strip()
                            
                            # Method 2: Direct text in td (for rowspan cells like user's HTML)
                            if not odds_value:
                                td_text = td.get_text(strip=True)
                                if re.match(r'^[+-]?\d+$', td_text):
                                    odds_value = td_text
                            
                            if odds_value:
                                totals_data[sportsbook] = odds_value
                    
                    all_totals_data.append(totals_data)
    
    if all_totals_data:
        df = pd.DataFrame(all_totals_data)
        for sportsbook in all_sportsbooks:
            if sportsbook not in df.columns:
                df[sportsbook] = ''
        # Ensure fighter columns exist even if some rows had no pairing context
        if 'Fighter1' not in df.columns:
            df['Fighter1'] = ''
        if 'Fighter2' not in df.columns:
            df['Fighter2'] = ''
        first_cols = ['Fighter1', 'Fighter2', 'Totals_Type']
        other_cols = [col for col in df.columns if col not in first_cols and col != 'Event']
        df = df[first_cols + other_cols + ['Event']]
        return df
    else:
        columns = ['Fighter1', 'Fighter2', 'Totals_Type'] + list(all_sportsbooks) + ['Event']
        return pd.DataFrame(columns=columns)

# TARGET_PROMOTION_KEYWORDS = ("ufc", "pfl", "lfa", "one", "oktagon", "cwfc", "cage-warriors", "rizin", "brave", "ksw", "uaew", "uae-warriors")
TARGET_PROMOTION_KEYWORDS = os.environ['TARGET_PROMOTION_KEYWORDS'].split(',')

def scrape_fightodds_totals():
    driver = setup_driver()
    driver.get("https://fightodds.io/")
    # Wait for page to load and nav to appear
    nav = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "nav"))
    )
    all_data = []
    try:
        target_event_links = []
        
        # Click promotion buttons
        promotion_buttons = nav.find_elements(By.CSS_SELECTOR, "div[role='button'], a[role='button']")
        clicked_promotions = set()
        for btn in promotion_buttons:
            btn_text = btn.text.strip().lower()
            for keyword in TARGET_PROMOTION_KEYWORDS:
                if keyword in btn_text:
                    if keyword not in clicked_promotions:
                        try:
                            driver.execute_script("arguments[0].click();", btn)
                            clicked_promotions.add(keyword)
                            # Brief wait for navigation to update after clicking
                            time.sleep(0.5)
                        except Exception as e:
                            print(f"Error clicking promotion button {btn_text}: {e}")
                        break
        
        # Brief wait for all navigation updates to complete
        time.sleep(1)
        
        # Find event links
        event_links = []
        event_links.extend(driver.find_elements(By.CSS_SELECTOR, "nav a[href*='/odds/']"))
        event_links.extend(driver.find_elements(By.CSS_SELECTOR, "a.MuiListItem-root[href*='/odds/']"))
        event_links.extend(driver.find_elements(By.CSS_SELECTOR, "a[role='button'][href*='/odds/']"))
        if len(event_links) == 0:
            event_links.extend(driver.find_elements(By.CSS_SELECTOR, "a[href*='/odds/']"))
        
        seen_hrefs = set()
        for link in event_links:
            try:
                href = link.get_attribute('href')
                text = clean_event_name(link.text)
                if not (href and text) or 'More Event' in text or href in seen_hrefs:
                    continue
                seen_hrefs.add(href)
                text_lower = text.lower()
                href_lower = href.lower()
                if any(keyword in text_lower for keyword in TARGET_PROMOTION_KEYWORDS):
                    target_event_links.append((text, href))
                    # Print only the first line (event name), skip numbers on subsequent lines
                    event_name_display = text.split('\n')[0].strip()
                    print(event_name_display)
            except Exception as e:
                print(f"Error processing event link: {e}")
                continue
        
        main_window = driver.current_window_handle
        for event_name, event_url in target_event_links:
            try:
                driver.execute_script(f"window.open('{event_url}', '_blank');")
                # Wait for new window to open
                WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
                windows = driver.window_handles
                if len(windows) > 1:
                    new_window = [w for w in windows if w != main_window][0]
                    try:
                        driver.switch_to.window(new_window)
                        
                        # Wait for page to be fully loaded
                        WebDriverWait(driver, 20).until(
                            lambda d: d.execute_script("return document.readyState") == "complete"
                        )
                        
                        # Check if table exists - some events may not have odds/totals yet
                        table = None
                        try:
                            table = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "MuiTable-root"))
                            )
                        except (TimeoutException, NoSuchElementException):
                            # Table doesn't exist, skip this event gracefully
                            pass
                        
                        if table:
                            # Scroll to table
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", table)
                            # Brief wait for scroll animation
                            time.sleep(0.5)
                            
                            # Try to find and click expand buttons if they exist
                            # Some events may not have expand buttons (no totals available yet)
                            try:
                                expand_buttons = driver.find_elements(By.CSS_SELECTOR, ".MuiTable-root tbody tr button.MuiButton-containedSizeSmall")
                                if expand_buttons:
                                    for button in expand_buttons:
                                        try:
                                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
                                            driver.execute_script("arguments[0].click();", button)
                                            time.sleep(0.5)
                                        except:
                                            pass
                                    # Brief wait for all expanded content to render
                                    time.sleep(1)
                            except:
                                # No expand buttons found or error, continue to parsing
                                pass
                            
                            # Parse totals from the page (they may appear as new rows or in popovers)
                            event_html = driver.page_source
                            event_data = parse_totals_table(event_html, event_name)
                            if not event_data.empty:
                                all_data.append(event_data)
                    except Exception as e:
                        print(f"Error scraping totals for event {event_name}: {e}")
                        import traceback
                        traceback.print_exc()
                    finally:
                        try:
                            driver.close()
                        except:
                            pass
                        try:
                            if main_window in driver.window_handles:
                                driver.switch_to.window(main_window)
                            elif driver.window_handles:
                                driver.switch_to.window(driver.window_handles[0])
                        except:
                            pass
                else:
                    print(f"Failed to open new window for {event_name}")
            except Exception as e:
                print(f"Error opening event {event_name}: {e}")
                import traceback
                traceback.print_exc()
                try:
                    if main_window in driver.window_handles:
                        driver.switch_to.window(main_window)
                    elif driver.window_handles:
                        driver.switch_to.window(driver.window_handles[0])
                except:
                    pass
    except Exception as e:
        print(f"Error in scrape_fightodds_totals: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
    
    if all_data:
        combined_data = pd.concat(all_data, ignore_index=True)
        return combined_data
    else:
        return pd.DataFrame()

# Main execution
try:
    totals_data = scrape_fightodds_totals()
    totals_file = os.path.join(script_dir, 'data', f'ufc_totals_fightoddsio_{datetime.now().strftime("%Y%m%d_%H%M")}.csv')
    os.makedirs(os.path.dirname(totals_file), exist_ok=True)
    
    if not totals_data.empty:
        totals_data.to_csv(totals_file, index=False)
        print("Totals data scraped and saved.")
    else:
        # Create empty file with headers to indicate script ran
        empty_df = pd.DataFrame(columns=['Totals_Type', 'Event'])
        empty_df.to_csv(totals_file, index=False)
        print("No totals data found.")
except Exception as e:
    print(f"Totals scrape failed: {e}")
    import traceback
    traceback.print_exc()

print("UFC Totals scraper finished")

os.system("rm -rf /tmp/chrome-temp")
print("Cleaned up temporary Chrome directory")


# from datadog import initialize, statsd
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

# --- Datadog setup: no API key needed, agent is local ---
# initialize(statsd_host="localhost", statsd_port=8125)

script_dir = os.path.dirname(os.path.abspath(__file__))
# vsin_failed = False  # VSIN disabled
fightodds_failed = False

print("UFC cron script started")


def register_driver_cleanup(driver):
    def _cleanup():
        try:
            driver.quit()
        except Exception:
            pass

    atexit.register(_cleanup)


def setup_driver():
    chromedriver_path = "/usr/bin/chromedriver"
    if not os.path.exists(chromedriver_path):
        chromedriver_path = "/opt/homebrew/bin/chromedriver"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-temp")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    # chrome_options.add_argument("--disable-images")
    # chrome_options.add_argument("--disable-javascript")  # We'll enable it selectively if needed
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_settings.popups": 0,
        "download.default_directory": "/tmp",
        "download.prompt_for_download": False
    })
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    register_driver_cleanup(driver)
    return driver

def scrape_vsin():
    driver = setup_driver()
    url = 'https://data.vsin.com/vegas-odds-linetracker/?sportid=ufc&linetype=moneyline'
    driver.get(url)
    data = []
    try:
        table_xpath = '/html/body/div[6]/div[2]/div/div[3]/div/div/div/div[2]/b/div[2]/table'
        table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, table_xpath))
        )
        table_children = table.find_elements(By.XPATH, './*')
        column_names = []
        for child in table_children:
            if child.tag_name.lower() == 'thead':
                header_cells = child.find_elements(By.XPATH, './tr/th')
                column_names = [cell.text.strip() if cell.text.strip() else f"Column{index+1}" 
                              for index, cell in enumerate(header_cells)]
            elif child.tag_name.lower() == 'tbody':
                rows = child.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    cell_data = [cell.text.strip() for cell in cells]
                    if cell_data:
                        max_length = max(len(cell_data), len(column_names))
                        cell_data.extend([None] * (max_length - len(cell_data)))
                        column_names.extend([f"ExtraColumn{index+1}" for index in range(len(column_names), max_length)])
                        row_data = {column_names[index]: value for index, value in enumerate(cell_data)}
                        data.append(row_data)
    finally:
        driver.quit()
    return data

def parse_odds_table(html_content, event_name="Unknown Event"):
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table', {'class': 'MuiTable-root'})
    all_fighters_data = []
    all_sportsbooks = set()
    for table in tables:
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                link = th.find('a')
                if link and link.get('href'):
                    sportsbook = link['href'].split('/')[-1]
                    all_sportsbooks.add(sportsbook)
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
                fighter_data = {'Event': event_name}
                fighter_link = tr.find('a')
                if fighter_link:
                    fighter_data['Fighters'] = fighter_link.text.strip()
                else:
                    continue
                odds_cells = tr.find_all('td')[1:-1]
                for i, td in enumerate(odds_cells):
                    if i < len(sportsbooks):
                        sportsbook = sportsbooks[i]
                        button = td.find('button')
                        if button:
                            # Try to find odds span - multiple patterns possible
                            odds_span = None
                            # Pattern 1: jss\d+ false (UFC/PFL style)
                            odds_span = button.find('span', {'class': re.compile('jss\\d+ false')})
                            # Pattern 2: jss\d+ (ONE Championship style) - look for span with jss class that contains odds
                            if not odds_span:
                                all_spans = button.find_all('span')
                                for span in all_spans:
                                    span_classes = span.get('class', [])
                                    if span_classes and any(re.match(r'jss\d+', str(c)) for c in span_classes):
                                        text = span.text.strip()
                                        # Check if it looks like odds (starts with + or - and has digits)
                                        if text and re.match(r'^[+-]?\d+$', text):
                                            odds_span = span
                                            break
                            if odds_span:
                                fighter_data[sportsbook] = odds_span.text.strip()
                all_fighters_data.append(fighter_data)
    if all_fighters_data:
        df = pd.DataFrame(all_fighters_data)
        for sportsbook in all_sportsbooks:
            if sportsbook not in df.columns:
                df[sportsbook] = ''
        first_cols = ['Event', 'Fighters']
        other_cols = [col for col in df.columns if col not in first_cols]
        df = df[first_cols + other_cols]
        return df
    else:
        columns = ['Event', 'Fighters'] + list(all_sportsbooks)
        return pd.DataFrame(columns=columns)

TARGET_PROMOTION_KEYWORDS = ("ufc", "pfl", "lfa", "one", "oktagon", "cwfc", "cage-warriors", "rizin", "brave", "ksw", "uaew", "uae-warriors")


def scrape_fightodds():
    driver = setup_driver()
    driver.get("https://fightodds.io/")
    time.sleep(3)
    all_data = []
    try:
        target_event_links = []
        
        nav = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "nav"))
        )
        
        # select both div and a elements that act as promotion buttons (some promos are <a role='button'>)
        promotion_buttons = nav.find_elements(By.CSS_SELECTOR, "div[role='button'], a[role='button']")
        clicked_promotions = set()
        for btn in promotion_buttons:
            btn_text = btn.text.strip().lower()
            for keyword in TARGET_PROMOTION_KEYWORDS:
                # match when keyword appears anywhere in the button text
                if keyword in btn_text:
                    if keyword not in clicked_promotions:
                        try:
                            driver.execute_script("arguments[0].click();", btn)
                            clicked_promotions.add(keyword)
                            time.sleep(2)
                        except Exception as e:
                            print(f"Error clicking promotion button {btn_text}: {e}")
                        break
        
        time.sleep(3)
        
        # Find event links - both regular links and links with role='button' (LFA/ONE style)
        # LFA events use: a.MuiButtonBase-root.MuiListItem-root with href containing '/odds/'
        # Try multiple selectors to catch all event link variations
        event_links = []
        # Selector 1: Standard links in nav
        event_links.extend(driver.find_elements(By.CSS_SELECTOR, "nav a[href*='/odds/']"))
        # Selector 2: MuiListItem with links (LFA/ONE style)
        event_links.extend(driver.find_elements(By.CSS_SELECTOR, "a.MuiListItem-root[href*='/odds/']"))
        # Selector 3: Any element with role='button' and href containing '/odds/'
        event_links.extend(driver.find_elements(By.CSS_SELECTOR, "a[role='button'][href*='/odds/']"))
        # Selector 4: Fallback - search entire page for odds links
        if len(event_links) == 0:
            event_links.extend(driver.find_elements(By.CSS_SELECTOR, "a[href*='/odds/']"))
        
        seen_hrefs = set()
        for link in event_links:
            try:
                href = link.get_attribute('href')
                text = link.text.strip()
                if not (href and text) or 'More Event' in text or href in seen_hrefs:
                    continue
                seen_hrefs.add(href)
                text_lower = text.lower()
                href_lower = href.lower()
                if any(keyword in text_lower or keyword in href_lower for keyword in TARGET_PROMOTION_KEYWORDS):
                    target_event_links.append((text, href))
                    # Print only the first line (event name), skip numbers on subsequent lines
                    event_name = text.split('\n')[0].strip()
                    print(event_name)
            except Exception as e:
                print(f"Error processing event link: {e}")
                continue
        
        if not target_event_links:
            print("No target event links found for specified promotions.")
        
        main_window = driver.current_window_handle
        for event_name, event_url in target_event_links:
            try:
                # Open in new window
                driver.execute_script(f"window.open('{event_url}', '_blank');")
                time.sleep(2)
                windows = driver.window_handles
                if len(windows) > 1:
                    new_window = [w for w in windows if w != main_window][0]
                    try:
                        driver.switch_to.window(new_window)
                        # Wait for table to appear, but handle empty events gracefully (LFA events may have no odds yet)
                        try:
                            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "MuiTable-root")))
                        except:
                            # If no table found, page might still be loading or event has no odds yet
                            time.sleep(2)
                        time.sleep(2)
                        event_html = driver.page_source
                        event_data = parse_odds_table(event_html, event_name)
                        if not event_data.empty:
                            all_data.append(event_data)
                    except Exception as e:
                        print(f"Error scraping event {event_name}: {e}")
                        import traceback
                        traceback.print_exc()
                    finally:
                        # Close the new window and switch back to main
                        try:
                            driver.close()
                        except:
                            pass
                        # Ensure we're back on main window
                        try:
                            if main_window in driver.window_handles:
                                driver.switch_to.window(main_window)
                            elif driver.window_handles:
                                driver.switch_to.window(driver.window_handles[0])
                        except:
                            pass
                        time.sleep(0.5)
                else:
                    print(f"Failed to open new window for {event_name}")
            except Exception as e:
                print(f"Error opening event {event_name}: {e}")
                import traceback
                traceback.print_exc()
                # Ensure we're on main window
                try:
                    if main_window in driver.window_handles:
                        driver.switch_to.window(main_window)
                    elif driver.window_handles:
                        driver.switch_to.window(driver.window_handles[0])
                except:
                    pass
    except Exception as e:
        print(f"Error in scrape_fightodds: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
    
    if all_data:
        combined_data = pd.concat(all_data, ignore_index=True)
        return combined_data
    else:
        return pd.DataFrame()

# Main execution with independent error handling for both parts
# vsin_succeeded = False  # VSIN disabled
fightodds_succeeded = False

# VSIN scraping disabled
# try:
#     # VSIN
#     try:
#         vsin_data = scrape_vsin()
#         vsin_file = os.path.join(script_dir, 'data', f'ufc_odds_vsin_{datetime.now().strftime("%Y%m%d_%H%M")}.json')
#         os.makedirs(os.path.dirname(vsin_file), exist_ok=True)
#         with open(vsin_file, 'w', encoding='utf-8') as f:
#             json.dump(vsin_data, f, ensure_ascii=False, indent=4)
#         vsin_succeeded = True
#         print("VSIN data scraped and saved.")
#     except Exception:
#         print("VSIN scrape failed")
# except Exception:
#     pass

# FightOdds
try:
    fightodds_data = scrape_fightodds()
    if not fightodds_data.empty:
        fightodds_file = os.path.join(script_dir, 'data', f'ufc_odds_fightoddsio_{datetime.now().strftime("%Y%m%d_%H%M")}.csv')
        os.makedirs(os.path.dirname(fightodds_file), exist_ok=True)
        fightodds_data.to_csv(fightodds_file, index=False)
        fightodds_succeeded = True
        print("FightOdds data scraped and saved.")
    else:
        print("FightOdds scrape returned no data.")
except Exception as e:
        print(f"FightOdds scrape failed: {e}")
        import traceback
        traceback.print_exc()
except Exception as e:
    print(f"Script execution failed: {e}")
    import traceback
    traceback.print_exc()

print("UFC cron script finished")

os.system("rm -rf /tmp/chrome-temp")
print("Cleaned up temporary Chrome directory")

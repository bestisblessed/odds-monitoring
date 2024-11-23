import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service  # Import Service
import json
import datetime
import csv
import os
from datetime import datetime
import time

### UFC ###

time.sleep(30)


chromedriver_path = "/usr/local/bin/chromedriver"
# chromedriver_path = "/opt/homebrew/bin/chromedriver"

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run Chrome in headless mode

# Specify the Service for ChromeDriver with the path
service = Service(chromedriver_path)

# Initialize the Chrome WebDriver with the options and service
driver = webdriver.Chrome(service=service, options=chrome_options)

# Navigate to the URL
url = 'https://data.vsin.com/vegas-odds-linetracker/?sportid=ufc&linetype=moneyline'
driver.get(url)

try:
    # Wait for the table to be present
    table_xpath = '/html/body/div[6]/div[2]/div/div[3]/div/div/div/div[2]/b/div[2]/table'
    table = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, table_xpath))
    )

    # Get all immediate child elements of the table (both thead and tbody)
    table_children = table.find_elements(By.XPATH, './*')

    # Initialize an empty list to hold all rows of data
    data = []

    # Initialize current column names as empty
    column_names = []

    # Iterate over each child element of the table
    for child in table_children:
        if child.tag_name.lower() == 'thead':
            # Extract column names from the header row
            header_cells = child.find_elements(By.XPATH, './tr/th')
            column_names = [cell.text.strip() for cell in header_cells]
            # Handle empty header names
            column_names = [name if name else f"Column{index+1}" for index, name in enumerate(column_names)]
        elif child.tag_name.lower() == 'tbody':
            # Use the current column names to extract data
            rows = child.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                cell_data = [cell.text.strip() for cell in cells]
                # Only add row if there is data
                if cell_data:
                    # Match the number of columns in data with column names
                    if len(cell_data) != len(column_names):
                        # Adjust cell_data or column_names if necessary
                        max_length = max(len(cell_data), len(column_names))
                        cell_data.extend([None] * (max_length - len(cell_data)))
                        column_names.extend([f"ExtraColumn{index+1}" for index in range(len(column_names), max_length)])
                    # Create a dictionary using column names as keys
                    row_data = {column_names[index]: value for index, value in enumerate(cell_data)}
                    data.append(row_data)
        else:
            # Other types of elements, skip or handle if needed
            pass

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Close the WebDriver
    driver.quit()

# Assuming current_time is already defined
timestamp = datetime.now().strftime("%Y%m%d_%H%M")

# Get the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Create the full path using the script's directory
filename = os.path.join(script_dir, 'data', f'ufc_odds_vsin_{timestamp}.json')

# Create the 'data' directory if it doesn't exist
os.makedirs(os.path.dirname(filename), exist_ok=True)

# Write the data to the JSON file
with open(filename, 'w', encoding='utf-8') as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)

print(f"Data has been saved to {filename}")

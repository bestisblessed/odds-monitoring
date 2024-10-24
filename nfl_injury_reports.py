# import selenium
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.chrome.service import Service  # Import Service
# from selenium.webdriver.support import expected_conditions as EC
# import json
# import datetime
# import csv
# import os
# from datetime import datetime
# import time

# ### NFL Injury Reports ###

# time.sleep(10)

# chromedriver_path = "/usr/local/bin/chromedriver"
# chrome_options = Options()
# chrome_options.add_argument("--headless")  # Run Chrome in headless mode
# service = Service(chromedriver_path)
# driver = webdriver.Chrome(service=service, options=chrome_options)

# # Navigate to the URL
# url = 'https://www.espn.com/nfl/injuries'
# driver.get(url)

# # Wait for the tables to load
# wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ResponsiveTable")))

# # Find all tables with the class "ResponsiveTable Table__league-injuries"
# tables = driver.find_elements(By.CLASS_NAME, "ResponsiveTable")

# # Loop through each table and extract the data from thead and tbody rows
# for table in tables:
#     # Extract the table header
#     thead = table.find_element(By.TAG_NAME, "thead")
#     header_cells = thead.find_elements(By.TAG_NAME, "th")
#     headers = [header.text for header in header_cells]
#     print("Headers:", headers)

#     # Extract the table rows
#     tbody = table.find_element(By.TAG_NAME, "tbody")
#     rows = tbody.find_elements(By.TAG_NAME, "tr")
    
#     for row in rows:
#         cells = row.find_elements(By.TAG_NAME, "td")
#         row_data = [cell.text for cell in cells]
#         print("Row data:", row_data)

# # Close the browser when done
# driver.quit()

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime
import os


# Configure Chrome options
# chromedriver_path = "/usr/local/bin/chromedriver"
chromedriver_path = "/opt/homebrew/bin/chromedriver"
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run Chrome in headless mode
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# Navigate to the URL
url = 'https://www.espn.com/nfl/injuries'
driver.get(url)

# Wait for the table to load
wait = WebDriverWait(driver, 10)
wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ResponsiveTable")))

# Find all tables with the class "ResponsiveTable Table__league-injuries"
tables = driver.find_elements(By.CLASS_NAME, "ResponsiveTable")

# Prepare a list to store the extracted table data
all_data = []

# Loop through each table and extract the data
for table in tables:
    # Extract the table header
    headers = [th.text for th in table.find_elements(By.TAG_NAME, "th")]
    
    # Extract the table rows
    rows = table.find_elements(By.TAG_NAME, "tr")
    
    for row in rows:
        row_data = [td.text for td in row.find_elements(By.TAG_NAME, "td")]
        if row_data:
            all_data.append(row_data)

# Convert the data into a DataFrame
df = pd.DataFrame(all_data, columns=headers)

# Make directory if it doesn't exist
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "data/injury-reports")
os.makedirs(output_dir, exist_ok=True)

today_date = datetime.now().strftime("%Y-%m-%d")
csv_file_path = os.path.join(output_dir, f"nfl_injury_status_{today_date}.csv")
df.to_csv(csv_file_path, index=False)

# Close the browser
driver.quit()

print(f"Data saved to {csv_file_path}")

import os
import re
from datetime import datetime

# Function to get the timestamp from the filename
def extract_timestamp(filename):
    match = re.search(r'nfl_odds_vsin_(\d{8}_\d{4})\.json', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y%m%d_%H%M')
    return None

# Function to filter files based on the end time
def filter_files_by_time(directory, end_time):
    files = os.listdir(directory)
    
    # Convert end_time to a datetime object
    end_time_dt = datetime.strptime(end_time, '%Y%m%d_%H%M')
    
    for file in files:
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            # Extract the timestamp from the filename
            file_timestamp = extract_timestamp(file)
            
            # If the file's timestamp is after the end time, delete it
            if file_timestamp and file_timestamp > end_time_dt:
                print(f"Deleting file: {file}")
                os.remove(file_path)

# Set the directory and end time
directory = 'data/'  # Directory where your files are stored
end_time = '20240929_1259'  # End time: Sep 29th at 12:59 PM (YYYYMMDD_HHMM)

# Call the function to filter files
filter_files_by_time(directory, end_time)

print("File filtering completed.")

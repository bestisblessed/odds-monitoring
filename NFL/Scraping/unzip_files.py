import os
import zipfile
from datetime import datetime
import logging
import re
import shutil
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/unzip.log'),
        logging.StreamHandler()
    ]
)
script_dir = os.path.dirname(os.path.abspath(__file__))
zip_dir = os.path.join(script_dir, 'zips')
data_dir = os.path.join(script_dir, 'data')
odds_dir = os.path.join(data_dir, 'odds')
os.makedirs(odds_dir, exist_ok=True)
if not os.path.exists(zip_dir):
    logging.error(f"Zip directory not found: {zip_dir}")
else:
    zip_files = [f for f in os.listdir(zip_dir) if f.endswith('.zip')]
    if not zip_files:
        logging.info("No zip files found to extract")
    else:
        def extract_date_from_filename(filename):
            match = re.search(r'_(\w{3})_(\d{2})_(\d{2})\.zip$', filename)
            if match:
                month_str, day, year = match.groups()
                month = datetime.strptime(month_str, '%b').month  # Convert month abbreviation to month number
                year = int('20' + year)  # Convert YY to YYYY
                return datetime(year, month, int(day))
            return datetime.min  # Default for files without a valid date
        sorted_zip_files = sorted(zip_files, key=extract_date_from_filename)
        for zip_file in sorted_zip_files:
            zip_path = os.path.join(zip_dir, zip_file)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(data_dir)
                    logging.info(f"Successfully extracted {zip_file}")
                    # os.remove(zip_path)
                    # logging.info(f"Deleted zip file: {zip_file}")
            except zipfile.BadZipFile:
                logging.error(f"Error: {zip_file} is not a valid zip file")
            except Exception as e:
                logging.error(f"Error extracting {zip_file}: {str(e)}")
extracted_data_dir = os.path.join(data_dir, 'data')
if os.path.exists(extracted_data_dir):
    for item in os.listdir(extracted_data_dir):
        shutil.move(os.path.join(extracted_data_dir, item), odds_dir)
    os.rmdir(extracted_data_dir)  
logging.info("Starting unzip process")
logging.info("Finished unzip process")
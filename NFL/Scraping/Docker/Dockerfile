FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y wget unzip vim chromium chromium-driver
RUN pip install --no-cache-dir -r requirements.txt
COPY nfl-docker.py .
CMD ["python", "nfl-docker.py"]



    # wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    # dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install && \
    # rm google-chrome-stable_current_amd64.deb && \
    # wget -q https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip && \
    # unzip chromedriver_linux64.zip -d /usr/local/bin && \
    # rm chromedriver_linux64.zip
# RUN apt-get update && \
    # apt-get install -y wget unzip chromium chromium-driver && \
    # rm -rf /var/lib/apt/lists/* \

# # Use the official Python image as a base
# FROM python:3.9-slim

# # Install necessary packages
# RUN apt-get update && apt-get install -y \
#     wget \
#     unzip \
#     && rm -rf /var/lib/apt/lists/*

# # Install Chrome
# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#     && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
#     && apt-get update \
#     && apt-get install -y google-chrome-stable

# # Install ChromeDriver
# RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` && \
#     wget -q --no-check-certificate -O /tmp/chromedriver_linux64.zip "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" && \
#     unzip /tmp/chromedriver_linux64.zip -d /usr/local/bin/ && \
#     rm /tmp/chromedriver_linux64.zip

# # Set environment variables
# ENV PYTHONUNBUFFERED=1

# # Set the working directory
# WORKDIR /app

# # Copy the requirements file and install dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the script into the container
# COPY . .

# # Run the script
# CMD ["python", "nfl.py"]
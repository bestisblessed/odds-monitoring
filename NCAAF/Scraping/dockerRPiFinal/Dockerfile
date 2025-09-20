# Use ARM64 compatible Python image for Raspberry Pi
FROM python:3.12-slim

# Install system dependencies for ARM64/Raspberry Pi
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    tzdata \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libxss1 \
    libxtst6 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set timezone to Eastern Time
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY ncaaf-docker.py .

# Create data directory
RUN mkdir -p data

# Run the script
CMD ["python", "ncaaf-docker.py"]

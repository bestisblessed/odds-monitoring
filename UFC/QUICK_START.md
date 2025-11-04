# UFC Pushover Monitor - Quick Start

## What I Found

**You didn't have a UFC Pushover monitor before** - only NFL and NCAAF had monitoring scripts. I've created one for you based on the same pattern.

## What I Created

1. ✅ **UFC Pushover Monitor** (`UFC/DASHBOARD-DASH/ufc_monitor_odds_movement.py`)
   - Detects odds movements from FightOdds.io data
   - Sends Pushover notifications for major sportsbooks
   - Ready to use

2. ✅ **Run Script** (`UFC/DASHBOARD-DASH/run_monitor.sh`)
   - Simple executable script to run the monitor

3. ✅ **Updated Requirements** (`UFC/Scraping/requirements.txt`)
   - Added missing dependencies (beautifulsoup4, pandas, requests)

4. ✅ **Cleaned Up Scraper** (`UFC/Scraping/ufc.py`)
   - Removed unused datadog imports
   - Cleaned up commented code

## Get Started in 3 Steps

### 1. Set Up Pushover

Get your credentials from https://pushover.net/ and add to your shell:

```bash
export PUSHOVER_USER_KEY="your_key_here"
export PUSHOVER_APP_TOKEN="your_token_here"
source ~/.bashrc
```

### 2. Test It

```bash
# Test scraper (needs Chrome + ChromeDriver)
cd UFC/Scraping
python3 ufc.py

# Wait 3 minutes, then run again to get a second data file

# Test monitor
cd ../DASHBOARD-DASH
python3 ufc_monitor_odds_movement.py
```

### 3. Add to Cron

```bash
crontab -e
```

Add these lines:

```bash
# Scrape UFC odds every 3 minutes
3-59/3 * * * * python3 $HOME/odds-monitoring/UFC/Scraping/ufc.py >> $HOME/odds-monitoring/logs/ufc_scraper.log 2>&1

# Check for odds movements 2 minutes after scraping
5-59/3 * * * * python3 $HOME/odds-monitoring/UFC/DASHBOARD-DASH/ufc_monitor_odds_movement.py >> $HOME/odds-monitoring/logs/ufc_monitor.log 2>&1
```

## Verified Working

✅ VSIN API - Online and responding  
✅ FightOdds.io - Online and responding  
✅ Pushover API - Active  
✅ Python 3.12.3 - Available  
✅ No linter errors  

## Need More Details?

See `UFC_MONITORING_SETUP.md` for complete documentation.

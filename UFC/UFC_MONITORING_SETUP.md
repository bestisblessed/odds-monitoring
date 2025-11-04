# UFC Odds Monitoring System

## Overview

Your UFC odds monitoring system consists of **two main components**:

### 1. **Data Scraping** (`UFC/Scraping/ufc.py`)
- Scrapes UFC odds from VSIN and FightOdds.io
- Runs every 3 minutes via cron
- Saves timestamped data files to `UFC/Scraping/data/`

### 2. **Odds Movement Monitor** (`UFC/DASHBOARD-DASH/ufc_monitor_odds_movement.py`) **[NEW]**
- Detects odds changes between consecutive scrapes
- Sends Pushover notifications when significant books move
- Monitors: DraftKings, FanDuel, BetMGM, Circa Sports, Caesars

---

## How It Works

```
┌─────────────────────┐
│  Every 3 minutes    │
│  ufc.py scrapes     │
│  VSIN & FightOdds   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Saves CSV files     │
│ ufc_odds_fightodds  │
│ io_YYYYMMDD_HHMM    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Monitor compares    │
│ last 2 files for    │
│ odds movements      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Sends Pushover      │
│ notification if     │
│ odds changed        │
└─────────────────────┘
```

---

## Setup Instructions

### Prerequisites

1. **Python 3.12+** with packages:
   ```bash
   cd UFC/Scraping
   pip install -r requirements.txt
   ```

2. **Chrome & Chromedriver**:
   - The scraper expects chromedriver at `/usr/bin/chromedriver`
   - Verify with: `which chromedriver`

3. **Pushover Account**:
   - Sign up at: https://pushover.net/
   - Get your User Key from the dashboard
   - Create an app and get the API Token

### Environment Variables

Set these in your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export PUSHOVER_USER_KEY="your_user_key_here"
export PUSHOVER_APP_TOKEN="your_app_token_here"
```

Then reload: `source ~/.bashrc`

---

## Running the Monitor

### Option 1: Manual Run

```bash
cd UFC/DASHBOARD-DASH
./run_monitor.sh
```

### Option 2: Automated with Cron (Recommended)

Add to your crontab (`crontab -e`):

```bash
# Scrape UFC odds every 3 minutes
3-59/3 * * * * $HOME/.pyenv/shims/python $HOME/odds-monitoring/UFC/Scraping/ufc.py >> $HOME/odds-monitoring/logs/ufc_scraper.log 2>&1

# Check for odds movements every 3 minutes (offset by 2 minutes after scraper)
5-59/3 * * * * $HOME/.pyenv/shims/python $HOME/odds-monitoring/UFC/DASHBOARD-DASH/ufc_monitor_odds_movement.py >> $HOME/odds-monitoring/logs/ufc_monitor.log 2>&1
```

This will:
- Scrape at :03, :06, :09, :12, etc.
- Check for movements at :05, :08, :11, :14, etc.

---

## Verification Steps

### 1. Test the Scraper

```bash
cd UFC/Scraping
python3 ufc.py
```

Expected output:
```
UFC cron script started
VSIN data scraped and saved.
FightOdds data scraped and saved.
UFC cron script finished
Cleaned up temporary Chrome directory
```

Check for data files:
```bash
ls -lh UFC/Scraping/data/
```

### 2. Test the Monitor

```bash
cd UFC/DASHBOARD-DASH
python3 ufc_monitor_odds_movement.py
```

Expected output:
```
No odds movements detected
```
or
```
Sending notification: [Fighter Name]
...
Processed 5 odds movements
```

### 3. Test Pushover Credentials

```bash
python3 -c "
import os
import requests
response = requests.post('https://api.pushover.net/1/messages.json', data={
    'token': os.environ['PUSHOVER_APP_TOKEN'],
    'user': os.environ['PUSHOVER_USER_KEY'],
    'message': 'UFC Monitor Test',
    'title': 'Test'
})
print(f'Status: {response.status_code}')
print(response.json())
"
```

Should return: `Status: 200`

---

## Troubleshooting

### Issue: "Pushover credentials not found"
**Solution**: Make sure environment variables are set:
```bash
echo $PUSHOVER_USER_KEY
echo $PUSHOVER_APP_TOKEN
```

### Issue: "Data directory not found"
**Solution**: Run the scraper first to create data:
```bash
cd UFC/Scraping && python3 ufc.py
```

### Issue: "Not enough data files to compare"
**Solution**: The monitor needs at least 2 scrapes. Wait 3 minutes for the second scrape.

### Issue: ChromeDriver errors
**Solution**: 
- Check Chrome version: `google-chrome --version`
- Check ChromeDriver version: `chromedriver --version`
- Ensure they match (e.g., both Chrome 120)
- Download correct version from: https://chromedriver.chromium.org/

---

## Data Storage

### Scraper Output Files
- **Location**: `UFC/Scraping/data/`
- **Format**: `ufc_odds_fightoddsio_YYYYMMDD_HHMM.csv`
- **Example**: `ufc_odds_fightoddsio_20251104_1430.csv`

### Monitor Behavior
- Compares the **last 2 files** in the data directory
- Only notifies for sportsbooks: DraftKings, FanDuel, BetMGM, Circa Sports, Caesars
- Each notification includes:
  - Fighter name
  - Event name
  - Sportsbook
  - Odds before → Odds after
  - Timestamp

---

## API Status

✅ **VSIN API**: `https://data.vsin.com/vegas-odds-linetracker/?sportid=ufc&linetype=moneyline`
   - Status: Active (verified 2025-11-04)

✅ **FightOdds.io**: `https://fightodds.io/`
   - Status: Active (verified 2025-11-04)

✅ **Pushover API**: `https://api.pushover.net/1/messages.json`
   - Status: Active
   - Documentation: https://pushover.net/api

---

## Customization

### Monitor Different Sportsbooks

Edit `ufc_monitor_odds_movement.py` line 77:

```python
sportsbooks_of_interest = ['draftkings', 'fanduel', 'betmgm', 'circa-sports', 'caesars']
```

Add or remove sportsbooks as needed. Check your CSV files for exact sportsbook names.

### Change Notification Frequency

Adjust the cron schedule:
```bash
# Every 5 minutes instead of 3
5-59/5 * * * * ...
```

### Notification Priority

Change priority in line 14 of `ufc_monitor_odds_movement.py`:
- `0` = Normal (default)
- `1` = High priority (bypasses quiet hours)
- `2` = Emergency (requires acknowledgment)

---

## Files Reference

| File | Purpose |
|------|---------|
| `UFC/Scraping/ufc.py` | Main scraper script |
| `UFC/Scraping/requirements.txt` | Python dependencies |
| `UFC/Scraping/data/` | Scraped odds data storage |
| `UFC/DASHBOARD-DASH/ufc_monitor_odds_movement.py` | Pushover notification monitor |
| `UFC/DASHBOARD-DASH/run_monitor.sh` | Helper script to run monitor |
| `cron.txt` | Example cron configuration |

---

## Next Steps

1. ✅ Set up Pushover credentials
2. ✅ Test the scraper manually
3. ✅ Test the monitor manually
4. ✅ Add to crontab
5. ✅ Monitor logs for any issues

**Log locations**:
- Scraper: `~/odds-monitoring/logs/ufc_scraper.log`
- Monitor: `~/odds-monitoring/logs/ufc_monitor.log`

Create log directory if needed:
```bash
mkdir -p ~/odds-monitoring/logs
```

---

## Support

For issues with:
- **Scraping**: Check Chrome/ChromeDriver compatibility
- **Notifications**: Verify Pushover credentials
- **Cron**: Check `crontab -l` and log files
- **APIs**: Test endpoints directly with curl

Last Updated: 2025-11-04

# UFC Odds Monitor - Cron Setup

## Run 3 Minutes After Scraper

Add this line to your crontab (runs 3 minutes after the UFC scraper completes)

3-59/4 * * * * /home/trinity/.pyenv/shims/python /home/trinity/odds-monitoring/UFC/Monitoring/ufc_monitor_odds_movement.py >> /home/trinity/odds-monitoring/UFC/Monitoring/ufc_monitor.log 2>&1

## Verify Cron

```bash
crontab -l
```


# UFC Odds Monitor - Cron Setup

Use the wrapper scripts from the `UFC/` folder instead of calling the monitor
Python files directly. The wrappers run the scraper first, export
`SCRAPE_MONEYLINES` / `SCRAPE_TOTALS`, and then run the selected monitor.

Do not schedule v1 and v2 at the same time unless you intentionally want two
separate alert paths. They read the same scraped data and seen-file state.

## v1: Normal Direct X API Version

This is the normal runtime path:

- Runner: `/home/durrrrr/odds-monitoring/UFC/run_scraper_and_monitor.sh`
- Monitor: `/home/durrrrr/odds-monitoring/UFC/Monitoring/ufc_monitor_odds_movement.py`
- Tweet path: direct X API via `POST https://api.x.com/2/tweets`
- Required X env vars: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

Crontab line:

```cron
*/4 * * * * /bin/bash /home/durrrrr/odds-monitoring/UFC/run_scraper_and_monitor.sh >> /home/durrrrr/odds-monitoring/UFC/cron_v1.log 2>&1
```

## v2: n8n Version

This is the n8n runtime path:

- Runner: `/home/durrrrr/odds-monitoring/UFC/run_scraper_and_monitor_with_n8n.sh`
- Compatibility runner: `/home/durrrrr/odds-monitoring/UFC/run_scraper_and_monitor_n8n.sh`
- Monitor: `/home/durrrrr/odds-monitoring/UFC/Monitoring/ufc_monitor_odds_movement_with_n8n.py`
- n8n sender: `send_n8n_opening_odds_webhook()` around line 404
- Required n8n env var: `N8N_OPENING_ODDS_WEBHOOK_URL` or `N8N_WEBHOOK_URL`

Crontab line:

```cron
*/4 * * * * /bin/bash /home/durrrrr/odds-monitoring/UFC/run_scraper_and_monitor_with_n8n.sh >> /home/durrrrr/odds-monitoring/UFC/cron_v2_n8n.log 2>&1
```

## Verify Cron

```bash
crontab -l
bash -n /home/durrrrr/odds-monitoring/UFC/run_scraper_and_monitor.sh
bash -n /home/durrrrr/odds-monitoring/UFC/run_scraper_and_monitor_with_n8n.sh
```

# UFC odds scraping and Supabase publish

`ufc_v2.py` writes timestamped FightOdds snapshots. Production cron
(`UFC/run_scraper_and_monitor.sh`) then publishes the latest snapshot:

```bash
python UFC/Scraping/supabase_odds_publisher.py --line-history --live
```

## Line-history retention

`ufc_odds_line_history` keeps compact odds segments. After a successful live
`--line-history` publish, the publisher deletes rows whose `last_seen_at` is
older than **14 days**:

```sql
DELETE FROM public.ufc_odds_line_history
WHERE last_seen_at < NOW() - INTERVAL '14 days';
```

Active open-board lines are not removed: each scrape refreshes `last_seen_at`
on the current segment. Only closed/stale segments fall out of the window.

Override the window with `--retain-days` or `UFC_LINE_HISTORY_RETAIN_DAYS`.
Use `0` to disable prune. Consumers that need more than 14 days of closed
segments must export beforehand.

Standalone prune (no snapshot publish):

```bash
python UFC/Scraping/supabase_odds_publisher.py --prune-line-history
python UFC/Scraping/supabase_odds_publisher.py --prune-line-history --live --retain-days 14
```

Optional ingest-run cleanup is off by default (`--prune-ingest-runs`, default
30 days, or `UFC_INGEST_RUNS_RETAIN_DAYS`).

Never deleted by this publisher: `ufc_fighters`, `ufc_fighter_source_map`,
`ufc_source_fights`.

`--print-schema` creates/maintains `ufc_odds_line_history` and
`ufc_odds_ingest_runs` only. `ufc_latest_odds` and `ufc_odds_history` are
retired and must not be recreated.

## Movement CSV (unchanged)

Local movement delivery to mma-ai Streamlit / mma-ai-swift is a separate path
(`update_ufc_data.sh` → `ufc_odds_movements_fightoddsio.csv`) and does not go
through this publisher.

import argparse
import csv
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR / "data"
DEFAULT_LATEST_TABLE = "ufc_latest_odds"
DEFAULT_HISTORY_TABLE = "ufc_odds_history"
DEFAULT_LINE_HISTORY_TABLE = "ufc_odds_line_history"
DEFAULT_INGEST_TABLE = "ufc_odds_ingest_runs"
LATEST_ON_CONFLICT = "source,market,event_name,fight_id,fighter,sportsbook"
HISTORY_ON_CONFLICT = "source,market,source_file,event_name,fight_id,fighter,sportsbook"
LINE_ON_CONFLICT = "source,market,event_name,fight_id,fighter,sportsbook,valid_from"
LINE_KEY_COLUMNS = ("source", "market", "event_name", "fight_id", "fighter", "sportsbook")
BASE_COLUMNS = {"Event", "Event_URL", "FightOdds_Fight_ID", "Fighters"}

SCHEMA_SQL = """
create table if not exists public.ufc_odds_history (
    source text not null,
    market text not null,
    source_file text not null,
    event_name text not null,
    fight_id text not null default '',
    event_raw text,
    event_url text,
    fighter text not null,
    sportsbook text not null,
    odds_american integer not null,
    scraped_at timestamptz not null,
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (source, market, source_file, event_name, fight_id, fighter, sportsbook)
);

create table if not exists public.ufc_latest_odds (
    source text not null,
    market text not null,
    event_name text not null,
    fight_id text not null default '',
    event_raw text,
    event_url text,
    fighter text not null,
    sportsbook text not null,
    odds_american integer not null,
    scraped_at timestamptz not null,
    source_file text not null,
    updated_at timestamptz not null default now(),
    primary key (source, market, event_name, fight_id, fighter, sportsbook)
);

create table if not exists public.ufc_odds_line_history (
    source text not null,
    market text not null,
    event_name text not null,
    fight_id text not null default '',
    event_raw text,
    event_url text,
    fighter text not null,
    sportsbook text not null,
    odds_american integer not null,
    valid_from timestamptz not null,
    last_seen_at timestamptz not null,
    first_source_file text not null,
    last_source_file text not null,
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (source, market, event_name, fight_id, fighter, sportsbook, valid_from)
);

alter table public.ufc_latest_odds
add column if not exists fight_id text not null default '';

alter table public.ufc_latest_odds
drop constraint if exists ufc_latest_odds_pkey;

alter table public.ufc_latest_odds
add primary key (source, market, event_name, fight_id, fighter, sportsbook);

create table if not exists public.ufc_odds_ingest_runs (
    id uuid primary key default gen_random_uuid(),
    source text not null default 'fightoddsio',
    market text not null default 'moneyline',
    source_file text not null,
    row_count integer not null check (row_count >= 0),
    scraped_at timestamptz,
    created_at timestamptz not null default now()
);

alter table public.ufc_latest_odds enable row level security;
alter table public.ufc_odds_history enable row level security;
alter table public.ufc_odds_line_history enable row level security;
alter table public.ufc_odds_ingest_runs enable row level security;

drop policy if exists "read ufc latest odds" on public.ufc_latest_odds;
drop policy if exists "read ufc odds history" on public.ufc_odds_history;
drop policy if exists "read ufc odds line history" on public.ufc_odds_line_history;
drop policy if exists "read ufc odds ingest runs" on public.ufc_odds_ingest_runs;

create policy "read ufc latest odds"
on public.ufc_latest_odds for select
to anon, authenticated
using (true);

create policy "read ufc odds history"
on public.ufc_odds_history for select
to anon, authenticated
using (true);

create policy "read ufc odds line history"
on public.ufc_odds_line_history for select
to anon, authenticated
using (true);

create policy "read ufc odds ingest runs"
on public.ufc_odds_ingest_runs for select
to anon, authenticated
using (true);

revoke all on table public.ufc_latest_odds from anon, authenticated;
revoke all on table public.ufc_odds_history from anon, authenticated;
revoke all on table public.ufc_odds_line_history from anon, authenticated;
revoke all on table public.ufc_odds_ingest_runs from anon, authenticated;
grant select on public.ufc_latest_odds to anon, authenticated;
grant select on public.ufc_odds_history to anon, authenticated;
grant select on public.ufc_odds_line_history to anon, authenticated;
grant select on public.ufc_odds_ingest_runs to anon, authenticated;
grant all on public.ufc_latest_odds to service_role;
grant all on public.ufc_odds_history to service_role;
grant all on public.ufc_odds_line_history to service_role;
grant all on public.ufc_odds_ingest_runs to service_role;

create index if not exists idx_ufc_odds_history_fighter_scraped_at
on public.ufc_odds_history (fighter, scraped_at);

create index if not exists idx_ufc_odds_history_source_file
on public.ufc_odds_history (source_file);

create index if not exists idx_ufc_odds_line_history_fighter_valid_from
on public.ufc_odds_line_history (fighter, valid_from);

create index if not exists idx_ufc_odds_line_history_last_seen_at
on public.ufc_odds_line_history (last_seen_at);

notify pgrst, 'reload schema';
"""


class SupabaseConfig:
    def __init__(
        self,
        url,
        service_role_key,
        history_table=DEFAULT_HISTORY_TABLE,
        line_history_table=DEFAULT_LINE_HISTORY_TABLE,
        latest_table=DEFAULT_LATEST_TABLE,
        ingest_table=DEFAULT_INGEST_TABLE,
        timeout=30,
    ):
        self.url = (url or "").rstrip("/")
        self.service_role_key = service_role_key or ""
        self.history_table = history_table
        self.line_history_table = line_history_table
        self.latest_table = latest_table
        self.ingest_table = ingest_table
        self.timeout = timeout


def find_all_csvs(data_dir=DEFAULT_DATA_DIR):
    return sorted(Path(data_dir).glob("ufc_odds_fightoddsio_*.csv"))


def find_latest_csv(data_dir=DEFAULT_DATA_DIR):
    files = find_all_csvs(data_dir)
    return files[-1] if files else None


def parse_scraped_at(source_file):
    match = re.search(r"ufc_odds_fightoddsio_(\d{8})_(\d{4})\.csv$", Path(source_file).name)
    if not match:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    timestamp = datetime.strptime("".join(match.groups()), "%Y%m%d%H%M")
    return timestamp.replace(tzinfo=timezone.utc).isoformat()


def parse_american_odds(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if value.is_integer():
            return int(value)

    text = str(value).strip()
    if not text or text == "-":
        return None
    if re.fullmatch(r"[+-]?\d+", text):
        return int(text.replace("+", ""))
    if re.fullmatch(r"[+-]?\d+\.0+", text):
        return int(float(text))
    return None


def clean_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def is_sportsbook_column(column_name):
    if column_name in BASE_COLUMNS:
        return False
    return not str(column_name).endswith("_URL")


def rows_from_dataframe(dataframe, source_file, scraped_at=None):
    scraped_at = scraped_at or parse_scraped_at(source_file)
    source_file_name = Path(source_file).name
    sportsbook_columns = [col for col in dataframe.columns if is_sportsbook_column(col)]
    rows = []

    for _, raw_row in dataframe.iterrows():
        event_raw = clean_text(raw_row.get("Event"))
        fighter = clean_text(raw_row.get("Fighters"))
        if not event_raw or not fighter:
            continue

        event_name = event_raw.splitlines()[0].strip()
        event_url = clean_text(raw_row.get("Event_URL")) or None
        fight_id = clean_text(raw_row.get("FightOdds_Fight_ID"))

        for sportsbook in sportsbook_columns:
            odds_american = parse_american_odds(raw_row.get(sportsbook))
            if odds_american is None:
                continue

            rows.append(
                {
                    "source": "fightoddsio",
                    "market": "moneyline",
                    "event_name": event_name,
                    "fight_id": fight_id,
                    "event_raw": event_raw,
                    "event_url": event_url,
                    "fighter": fighter,
                    "sportsbook": sportsbook,
                    "odds_american": odds_american,
                    "scraped_at": scraped_at,
                    "source_file": source_file_name,
                }
            )

    return rows


def iter_rows_from_csv(csv_path):
    csv_path = Path(csv_path)
    scraped_at = parse_scraped_at(csv_path)
    source_file_name = csv_path.name

    try:
        csv_file = csv_path.open(newline="", encoding="utf-8-sig")
    except OSError:
        raise

    with csv_file:
        try:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames:
                raise pd.errors.EmptyDataError("No columns to parse from file")
            sportsbook_columns = [col for col in reader.fieldnames if is_sportsbook_column(col)]

            for raw_row in reader:
                event_raw = clean_text(raw_row.get("Event"))
                fighter = clean_text(raw_row.get("Fighters"))
                if not event_raw or not fighter:
                    continue

                event_name = event_raw.splitlines()[0].strip()
                event_url = clean_text(raw_row.get("Event_URL")) or None
                fight_id = clean_text(raw_row.get("FightOdds_Fight_ID"))

                for sportsbook in sportsbook_columns:
                    odds_american = parse_american_odds(raw_row.get(sportsbook))
                    if odds_american is None:
                        continue

                    yield {
                        "source": "fightoddsio",
                        "market": "moneyline",
                        "event_name": event_name,
                        "fight_id": fight_id,
                        "event_raw": event_raw,
                        "event_url": event_url,
                        "fighter": fighter,
                        "sportsbook": sportsbook,
                        "odds_american": odds_american,
                        "scraped_at": scraped_at,
                        "source_file": source_file_name,
                    }
        except csv.Error as exc:
            raise pd.errors.ParserError(str(exc)) from exc


def chunked(values, size):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def supabase_headers(config, prefer):
    return {
        "apikey": config.service_role_key,
        "Authorization": f"Bearer {config.service_role_key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def post_rest(session, config, table_name, payload, params=None, prefer="return=minimal"):
    response = session.post(
        f"{config.url}/rest/v1/{table_name}",
        json=payload,
        params=params,
        headers=supabase_headers(config, prefer),
        timeout=config.timeout,
    )
    try:
        response.raise_for_status()
    except Exception as exc:
        detail = getattr(response, "text", "")
        status_code = getattr(response, "status_code", "unknown")
        raise RuntimeError(
            f"Supabase REST write failed for {table_name}: HTTP {status_code} {detail}"
        ) from exc
    return response


def get_rest(session, config, table_name, params=None):
    response = session.get(
        f"{config.url}/rest/v1/{table_name}",
        params=params,
        headers={
            "apikey": config.service_role_key,
            "Authorization": f"Bearer {config.service_role_key}",
        },
        timeout=config.timeout,
    )
    try:
        response.raise_for_status()
    except Exception as exc:
        detail = getattr(response, "text", "")
        status_code = getattr(response, "status_code", "unknown")
        raise RuntimeError(
            f"Supabase REST read failed for {table_name}: HTTP {status_code} {detail}"
        ) from exc
    return response.json()


def ingest_payload_from_rows(rows):
    if not rows:
        return []

    grouped = {}
    for row in rows:
        source_file = row.get("source_file", "")
        if source_file not in grouped:
            grouped[source_file] = {
                "source": row.get("source", "fightoddsio"),
                "market": row.get("market", "moneyline"),
                "source_file": source_file,
                "row_count": 0,
                "scraped_at": row.get("scraped_at"),
            }
        grouped[source_file]["row_count"] += 1

    return [grouped[key] for key in sorted(grouped)]


def history_key(row):
    return tuple(row.get(column, "") for column in HISTORY_ON_CONFLICT.split(","))


def line_key(row):
    return tuple(row.get(column, "") for column in LINE_KEY_COLUMNS)


def line_segment_from_row(row, valid_from=None, last_seen_at=None, first_source_file=None, last_source_file=None):
    scraped_at = row.get("scraped_at")
    source_file = row.get("source_file")
    return {
        "source": row.get("source", "fightoddsio"),
        "market": row.get("market", "moneyline"),
        "event_name": row.get("event_name", ""),
        "fight_id": row.get("fight_id", ""),
        "event_raw": row.get("event_raw"),
        "event_url": row.get("event_url"),
        "fighter": row.get("fighter", ""),
        "sportsbook": row.get("sportsbook", ""),
        "odds_american": row.get("odds_american"),
        "valid_from": valid_from or scraped_at,
        "last_seen_at": last_seen_at or scraped_at,
        "first_source_file": first_source_file or source_file,
        "last_source_file": last_source_file or source_file,
    }


def latest_line_seen_at(session, config):
    rows = get_rest(
        session,
        config,
        config.line_history_table,
        {
            "select": "last_seen_at",
            "source": "eq.fightoddsio",
            "market": "eq.moneyline",
            "order": "last_seen_at.desc",
            "limit": "1",
        },
    )
    return rows[0]["last_seen_at"] if rows else None


def fetch_active_line_rows(session, config, last_seen_at, page_size=1000):
    if not last_seen_at:
        return []

    rows = []
    offset = 0
    while True:
        batch = get_rest(
            session,
            config,
            config.line_history_table,
            {
                "select": (
                    "source,market,event_name,fight_id,event_raw,event_url,fighter,sportsbook,"
                    "odds_american,valid_from,last_seen_at,first_source_file,last_source_file"
                ),
                "source": "eq.fightoddsio",
                "market": "eq.moneyline",
                "last_seen_at": f"eq.{last_seen_at}",
                "limit": str(page_size),
                "offset": str(offset),
            },
        )
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += len(batch)
    return rows


def build_line_segments_for_snapshot(rows, active_rows=None):
    active_by_key = {line_key(row): row for row in active_rows or []}
    deduped = {}
    for row in rows:
        deduped[line_key(row)] = row

    segments = []
    extended_count = 0
    inserted_count = 0
    for row in deduped.values():
        active = active_by_key.get(line_key(row))
        if active and int(active.get("odds_american")) == int(row.get("odds_american")):
            segments.append(
                line_segment_from_row(
                    row,
                    valid_from=active.get("valid_from"),
                    last_seen_at=row.get("scraped_at"),
                    first_source_file=active.get("first_source_file"),
                    last_source_file=row.get("source_file"),
                )
            )
            extended_count += 1
        else:
            segments.append(line_segment_from_row(row))
            inserted_count += 1

    return {
        "segments": segments,
        "extended_segment_count": extended_count,
        "inserted_segment_count": inserted_count,
    }


def count_duplicate_history_keys(rows):
    seen = set()
    duplicate_count = 0
    for row in rows:
        key = history_key(row)
        if key in seen:
            duplicate_count += 1
        else:
            seen.add(key)
    return duplicate_count


def build_publish_result(dry_run, rows, csv_paths, history_table, ingest_table, skipped_files=None):
    rows = list(rows)
    skipped_files = list(skipped_files or [])
    scraped_values = sorted(
        str(row.get("scraped_at"))
        for row in rows
        if row.get("scraped_at")
    )
    result = {
        "dry_run": dry_run,
        "file_count": len(csv_paths),
        "row_count": len(rows),
        "duplicate_key_count": count_duplicate_history_keys(rows),
        "history_table": history_table,
        "ingest_table": ingest_table,
        "processed_file_count": len(csv_paths) - len(skipped_files),
        "skipped_file_count": len(skipped_files),
        "skipped_files": skipped_files,
        "min_scraped_at": scraped_values[0] if scraped_values else None,
        "max_scraped_at": scraped_values[-1] if scraped_values else None,
        "sample_rows": rows[:3],
    }
    if len(csv_paths) == 1:
        result["csv_path"] = str(csv_paths[0])
    else:
        result["csv_paths"] = [str(path) for path in csv_paths]
    return result


def publish_rows(
    config,
    rows,
    session=None,
    dry_run=True,
    chunk_size=500,
    csv_paths=None,
    skipped_files=None,
):
    rows = list(rows)
    csv_paths = list(csv_paths or [])
    if not csv_paths:
        csv_paths = [Path(row["source_file"]) for row in rows[:1] if row.get("source_file")]

    result = build_publish_result(
        dry_run=dry_run,
        rows=rows,
        csv_paths=csv_paths,
        history_table=config.history_table,
        ingest_table=config.ingest_table,
        skipped_files=skipped_files,
    )
    if dry_run:
        return result

    if not config.url or not config.service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for live publish.")

    session = session or requests.Session()
    for batch in chunked(rows, chunk_size):
        post_rest(
            session,
            config,
            config.history_table,
            batch,
            params={"on_conflict": HISTORY_ON_CONFLICT},
            prefer="resolution=merge-duplicates,return=minimal",
        )

    ingest_payload = ingest_payload_from_rows(rows)
    if ingest_payload:
        post_rest(session, config, config.ingest_table, ingest_payload, prefer="return=minimal")

    return result


def publish_line_rows(
    config,
    rows,
    session=None,
    dry_run=True,
    chunk_size=500,
    csv_paths=None,
    skipped_files=None,
):
    rows = list(rows)
    csv_paths = list(csv_paths or [])
    if not csv_paths:
        csv_paths = [Path(row["source_file"]) for row in rows[:1] if row.get("source_file")]

    if dry_run:
        line_build = build_line_segments_for_snapshot(rows)
    else:
        if not config.url or not config.service_role_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for live publish.")
        session = session or requests.Session()
        previous_seen_at = latest_line_seen_at(session, config)
        active_rows = fetch_active_line_rows(session, config, previous_seen_at)
        line_build = build_line_segments_for_snapshot(rows, active_rows=active_rows)

    result = build_publish_result(
        dry_run=dry_run,
        rows=rows,
        csv_paths=csv_paths,
        history_table=config.line_history_table,
        ingest_table=config.ingest_table,
        skipped_files=skipped_files,
    )
    result["line_history_table"] = config.line_history_table
    result["line_segment_count"] = len(line_build["segments"])
    result["extended_segment_count"] = line_build["extended_segment_count"]
    result["inserted_segment_count"] = line_build["inserted_segment_count"]

    if dry_run:
        return result

    for batch in chunked(line_build["segments"], chunk_size):
        post_rest(
            session,
            config,
            config.line_history_table,
            batch,
            params={"on_conflict": LINE_ON_CONFLICT},
            prefer="resolution=merge-duplicates,return=minimal",
        )

    ingest_payload = ingest_payload_from_rows(rows)
    if ingest_payload:
        post_rest(session, config, config.ingest_table, ingest_payload, prefer="return=minimal")

    return result


def build_config_from_env(
    history_table=DEFAULT_HISTORY_TABLE,
    line_history_table=DEFAULT_LINE_HISTORY_TABLE,
    latest_table=DEFAULT_LATEST_TABLE,
    ingest_table=DEFAULT_INGEST_TABLE,
):
    url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    missing = []
    if not url:
        missing.append("SUPABASE_URL")
    if not service_role_key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise RuntimeError(f"Set {', '.join(missing)} before using --live.")
    return SupabaseConfig(
        url,
        service_role_key,
        history_table=history_table,
        line_history_table=line_history_table,
        latest_table=latest_table,
        ingest_table=ingest_table,
    )


def load_rows_from_csv(csv_path):
    return list(iter_rows_from_csv(csv_path))


def load_rows_from_csvs(csv_paths, skip_invalid=False):
    rows = []
    skipped_files = []
    for csv_path in csv_paths:
        try:
            rows.extend(load_rows_from_csv(csv_path))
        except pd.errors.EmptyDataError as exc:
            if not skip_invalid:
                raise RuntimeError(f"{csv_path} is an empty CSV and cannot be published.") from exc
            skipped_files.append({"csv_path": str(csv_path), "reason": "empty_csv"})
        except pd.errors.ParserError as exc:
            if not skip_invalid:
                raise RuntimeError(f"{csv_path} could not be parsed as CSV: {exc}") from exc
            skipped_files.append({"csv_path": str(csv_path), "reason": "parser_error"})
    return rows, skipped_files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Dry-run or publish FightOdds CSV odds to Supabase.")
    parser.add_argument("--csv-path", type=Path)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--all", "--backfill", dest="backfill_all", action="store_true")
    parser.add_argument("--history-table", default=DEFAULT_HISTORY_TABLE)
    parser.add_argument("--line-history-table", default=DEFAULT_LINE_HISTORY_TABLE)
    parser.add_argument("--latest-table", default=DEFAULT_LATEST_TABLE)
    parser.add_argument("--ingest-table", default=DEFAULT_INGEST_TABLE)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--line-history", action="store_true", help="Publish compact odds line-history segments.")
    parser.add_argument("--live", action="store_true", help="Actually upsert rows into Supabase.")
    parser.add_argument("--print-schema", action="store_true", help="Print the expected table SQL.")
    args = parser.parse_args(argv)

    if args.print_schema:
        print(SCHEMA_SQL.strip())
        return 0

    if args.csv_path and args.backfill_all:
        raise SystemExit("Use either --csv-path or --all, not both.")

    if args.backfill_all:
        csv_paths = find_all_csvs(args.data_dir)
    else:
        csv_path = args.csv_path or find_latest_csv(args.data_dir)
        csv_paths = [csv_path] if csv_path is not None else []

    if not csv_paths:
        raise SystemExit(f"No ufc_odds_fightoddsio_*.csv files found in {args.data_dir}")

    try:
        rows, skipped_files = load_rows_from_csvs(csv_paths, skip_invalid=args.backfill_all)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    config = (
        build_config_from_env(
            args.history_table,
            args.line_history_table,
            args.latest_table,
            args.ingest_table,
        )
        if args.live
        else SupabaseConfig(
            "",
            "",
            history_table=args.history_table,
            line_history_table=args.line_history_table,
            latest_table=args.latest_table,
            ingest_table=args.ingest_table,
        )
    )
    publish_func = publish_line_rows if args.line_history else publish_rows
    result = publish_func(
        config,
        rows,
        dry_run=not args.live,
        chunk_size=args.chunk_size,
        csv_paths=csv_paths,
        skipped_files=skipped_files,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import csv
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from supabase_odds_publisher import (
    DEFAULT_DATA_DIR,
    DEFAULT_HISTORY_TABLE,
    DEFAULT_INGEST_TABLE,
    DEFAULT_LINE_HISTORY_TABLE,
    HISTORY_ON_CONFLICT,
    LINE_ON_CONFLICT,
    clean_text,
    find_all_csvs,
    history_key,
    iter_rows_from_csv,
    line_key,
    line_segment_from_row,
    parse_scraped_at,
)


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "bulk_import"
MANIFEST_NAME = "ufc_odds_history_manifest.json"
LOAD_SQL_NAME = "load_ufc_odds_history.sql"
VERIFY_SQL_NAME = "verify_ufc_odds_history.sql"
PART_PREFIX = "ufc_odds_history_part_"
LINE_MANIFEST_NAME = "ufc_odds_line_history_manifest.json"
LINE_LOAD_SQL_NAME = "load_ufc_odds_line_history.sql"
LINE_VERIFY_SQL_NAME = "verify_ufc_odds_line_history.sql"
LINE_PART_PREFIX = "ufc_odds_line_history_part_"
HISTORY_COLUMNS = [
    "source",
    "market",
    "source_file",
    "event_name",
    "fight_id",
    "event_raw",
    "event_url",
    "fighter",
    "sportsbook",
    "odds_american",
    "scraped_at",
]
LINE_HISTORY_COLUMNS = [
    "source",
    "market",
    "event_name",
    "fight_id",
    "event_raw",
    "event_url",
    "fighter",
    "sportsbook",
    "odds_american",
    "valid_from",
    "last_seen_at",
    "first_source_file",
    "last_source_file",
]


class ChunkedCsvWriter:
    def __init__(self, output_dir, rows_per_file, columns=None, part_prefix=PART_PREFIX):
        if rows_per_file < 1:
            raise ValueError("--rows-per-file must be at least 1")
        self.output_dir = Path(output_dir)
        self.rows_per_file = rows_per_file
        self.columns = columns or HISTORY_COLUMNS
        self.part_prefix = part_prefix
        self.part_paths = []
        self.current_rows = 0
        self.total_rows = 0
        self._handle = None
        self._writer = None

    def write_row(self, row):
        if self._writer is None or self.current_rows >= self.rows_per_file:
            self._open_next_part()
        self._writer.writerow({column: row.get(column) for column in self.columns})
        self.current_rows += 1
        self.total_rows += 1

    def close(self):
        if self._handle is not None:
            self._handle.close()
            self._handle = None
            self._writer = None

    def _open_next_part(self):
        self.close()
        part_number = len(self.part_paths) + 1
        path = self.output_dir / f"{self.part_prefix}{part_number:04d}.csv"
        self._handle = path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._handle, fieldnames=self.columns)
        self._writer.writeheader()
        self.part_paths.append(path)
        self.current_rows = 0


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def ensure_output_dir(output_dir, overwrite=False):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = list(output_dir.glob(f"{PART_PREFIX}*.csv"))
    generated_files.extend(output_dir.glob(f"{LINE_PART_PREFIX}*.csv"))
    generated_files.extend(
        path for path in [
            output_dir / MANIFEST_NAME,
            output_dir / LOAD_SQL_NAME,
            output_dir / VERIFY_SQL_NAME,
            output_dir / LINE_MANIFEST_NAME,
            output_dir / LINE_LOAD_SQL_NAME,
            output_dir / LINE_VERIFY_SQL_NAME,
        ]
        if path.exists()
    )
    if generated_files and not overwrite:
        generated = ", ".join(str(path) for path in generated_files[:5])
        extra = "" if len(generated_files) <= 5 else f", and {len(generated_files) - 5} more"
        raise RuntimeError(
            f"{output_dir} already contains generated bulk import files: {generated}{extra}. "
            "Use --overwrite to replace them."
        )
    if overwrite:
        for path in generated_files:
            if path.is_file():
                path.unlink()


def update_matchup_stats(matchup_stats, matchup_index, event_name, fight_id, fighters, source_file, scraped_at):
    fighters = tuple(sorted(clean_text(fighter) for fighter in fighters if clean_text(fighter)))
    if len(fighters) != 2 or not event_name:
        return

    key = (event_name, fight_id or "", fighters)
    stats = matchup_stats.setdefault(
        key,
        {
            "event_name": event_name,
            "fight_id": fight_id or "",
            "fighters": fighters,
            "source_files": set(),
            "scraped_at": set(),
            "compiled_row_count": 0,
        },
    )
    stats["source_files"].add(source_file)
    stats["scraped_at"].add(scraped_at)
    for fighter in fighters:
        matchup_index[(event_name, fight_id or "", fighter)] = stats


def update_matchup_row_count(matchup_index, row):
    key = (row.get("event_name") or "", row.get("fight_id") or "", row.get("fighter") or "")
    stats = matchup_index.get(key)
    if stats is not None:
        stats["compiled_row_count"] += 1


def update_matchup_stats_from_csv(matchup_stats, matchup_index, csv_path):
    csv_path = Path(csv_path)
    scraped_at = parse_scraped_at(csv_path)
    by_fight_id = {}
    fallback_rows = []

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise pd.errors.EmptyDataError("No columns to parse from file")

        for raw_row in reader:
            event_raw = clean_text(raw_row.get("Event"))
            fighter = clean_text(raw_row.get("Fighters"))
            if not event_raw or not fighter:
                continue

            event_name = event_raw.splitlines()[0].strip()
            fight_id = clean_text(raw_row.get("FightOdds_Fight_ID"))
            if fight_id:
                by_fight_id.setdefault((event_name, fight_id), set()).add(fighter)
            else:
                fallback_rows.append((event_name, fighter))

    for (event_name, fight_id), fighters in by_fight_id.items():
        if len(fighters) == 2:
            update_matchup_stats(
                matchup_stats,
                matchup_index,
                event_name,
                fight_id,
                fighters,
                csv_path.name,
                scraped_at,
            )

    pending_by_event = {}
    for event_name, fighter in fallback_rows:
        pending = pending_by_event.setdefault(event_name, [])
        pending.append(fighter)
        if len(pending) == 2:
            update_matchup_stats(
                matchup_stats,
                matchup_index,
                event_name,
                "",
                pending,
                csv_path.name,
                scraped_at,
            )
            pending_by_event[event_name] = []


def summarize_matchup_samples(matchup_stats, sample_count):
    summaries = []
    for stats in matchup_stats.values():
        if len(stats["scraped_at"]) < 2:
            continue
        scraped_values = sorted(value for value in stats["scraped_at"] if value)
        summaries.append(
            {
                "event_name": stats["event_name"],
                "fight_id": stats["fight_id"],
                "fighters": list(stats["fighters"]),
                "source_file_count": len([value for value in stats["source_files"] if value]),
                "scraped_at_count": len(scraped_values),
                "compiled_row_count": stats["compiled_row_count"],
                "min_scraped_at": scraped_values[0] if scraped_values else None,
                "max_scraped_at": scraped_values[-1] if scraped_values else None,
            }
        )

    summaries.sort(
        key=lambda item: (
            item["scraped_at_count"],
            item["source_file_count"],
            item["compiled_row_count"],
        ),
        reverse=True,
    )
    return summaries[:sample_count]


def stage_table_sql():
    return """
create temp table ufc_odds_history_stage (
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
    scraped_at timestamptz not null
) on commit drop;
""".strip()


def deduped_cte_sql():
    conflict_columns = ", ".join(HISTORY_ON_CONFLICT.split(","))
    return f"""
deduped as (
    select distinct on ({conflict_columns})
        source,
        market,
        source_file,
        event_name,
        fight_id,
        event_raw,
        event_url,
        fighter,
        sportsbook,
        odds_american,
        scraped_at
    from ufc_odds_history_stage
    order by {conflict_columns}, scraped_at desc
)
""".strip()


def upsert_history_sql(history_table=DEFAULT_HISTORY_TABLE):
    columns = ", ".join(HISTORY_COLUMNS)
    update_assignments = """
    event_raw = excluded.event_raw,
    event_url = excluded.event_url,
    odds_american = excluded.odds_american,
    scraped_at = excluded.scraped_at,
    updated_at = now()
""".strip()
    return f"""
with {deduped_cte_sql()}
insert into public.{history_table} ({columns})
select {columns}
from deduped
on conflict ({HISTORY_ON_CONFLICT}) do update set
{update_assignments};
""".strip()


def insert_ingest_sql(ingest_table=DEFAULT_INGEST_TABLE):
    return f"""
with {deduped_cte_sql()},
per_file as (
    select
        source,
        market,
        source_file,
        count(*)::integer as row_count,
        min(scraped_at) as scraped_at
    from deduped
    group by source, market, source_file
)
insert into public.{ingest_table} (source, market, source_file, row_count, scraped_at)
select source, market, source_file, row_count, scraped_at
from per_file
where not exists (
    select 1
    from public.{ingest_table} existing
    where existing.source = per_file.source
      and existing.market = per_file.market
      and existing.source_file = per_file.source_file
);
""".strip()


def render_load_sql(part_paths, history_table=DEFAULT_HISTORY_TABLE, ingest_table=DEFAULT_INGEST_TABLE):
    lines = [
        "\\set ON_ERROR_STOP on",
        "\\timing on",
        "set statement_timeout = '0';",
        "",
    ]
    columns = ", ".join(HISTORY_COLUMNS)
    for index, part_path in enumerate(part_paths, start=1):
        path = Path(part_path).resolve()
        lines.extend(
            [
                f"\\echo Loading odds history part {index}/{len(part_paths)}: {path.name}",
                "begin;",
                stage_table_sql(),
                f"\\copy ufc_odds_history_stage ({columns}) from {sql_literal(path)} with (format csv, header true)",
                upsert_history_sql(history_table),
                insert_ingest_sql(ingest_table),
                "commit;",
                "",
            ]
        )
    lines.extend(
        [
            f"analyze public.{history_table};",
            f"analyze public.{ingest_table};",
            "",
        ]
    )
    return "\n".join(lines)


def render_verify_sql(manifest, history_table=DEFAULT_HISTORY_TABLE):
    samples = manifest.get("matchup_samples") or manifest.get("fight_samples") or []
    lines = [
        "\\set ON_ERROR_STOP on",
        "\\timing on",
        "",
        f"select count(*)::bigint as total_rows, count(distinct source_file)::bigint as source_files, min(scraped_at) as min_scraped_at, max(scraped_at) as max_scraped_at from public.{history_table};",
        "",
    ]
    if not samples:
        lines.append(
            "select 'No compiled fights had at least two fighters and two timestamps.' as verification_note;"
        )
        return "\n".join(lines)

    values = []
    for sample in samples:
        fighters = sample.get("fighters") or ["", ""]
        values.append(
            "("
            f"{sql_literal(sample['event_name'])}, "
            f"{sql_literal(sample['fight_id'])}, "
            f"{sql_literal(fighters[0])}, "
            f"{sql_literal(fighters[1])}, "
            f"{int(sample.get('compiled_row_count', sample.get('row_count', 0)))}, "
            f"{int(sample['scraped_at_count'])}, "
            f"{int(sample['source_file_count'])}"
            ")"
        )

    values_sql = ",\n        ".join(values)

    lines.append(
        f"""
with expected(event_name, fight_id, fighter_one, fighter_two, expected_rows, expected_timestamps, expected_source_files) as (
    values
        {values_sql}
),
actual as (
    select
        expected.event_name,
        expected.fight_id,
        expected.fighter_one,
        expected.fighter_two,
        count(history.*)::integer as actual_rows,
        count(distinct history.scraped_at)::integer as actual_timestamps,
        count(distinct history.source_file)::integer as actual_source_files,
        min(history.scraped_at) as min_scraped_at,
        max(history.scraped_at) as max_scraped_at,
        array_agg(distinct history.fighter order by history.fighter) filter (where history.fighter is not null) as fighters
    from expected
    left join public.{history_table} history
      on history.event_name = expected.event_name
     and history.fighter in (expected.fighter_one, expected.fighter_two)
     and (expected.fight_id = '' or history.fight_id = expected.fight_id)
    group by expected.event_name, expected.fight_id, expected.fighter_one, expected.fighter_two
)
select
    expected.event_name,
    expected.fight_id,
    array[expected.fighter_one, expected.fighter_two] as expected_fighters,
    actual.fighters,
    expected.expected_rows,
    actual.actual_rows,
    expected.expected_timestamps,
    actual.actual_timestamps,
    expected.expected_source_files,
    actual.actual_source_files,
    actual.min_scraped_at,
    actual.max_scraped_at,
    actual.actual_rows >= expected.expected_rows
      and actual.actual_timestamps >= expected.expected_timestamps
      and actual.actual_source_files >= expected.expected_source_files
      as loaded_all_compiled_history
from expected
left join actual using (event_name, fight_id, fighter_one, fighter_two)
order by expected.expected_timestamps desc, expected.expected_rows desc;
""".strip()
    )
    return "\n".join(lines) + "\n"


def line_stage_table_sql():
    return """
create temp table ufc_odds_line_history_stage (
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
    last_source_file text not null
) on commit drop;
""".strip()


def upsert_line_history_sql(line_history_table=DEFAULT_LINE_HISTORY_TABLE):
    columns = ", ".join(LINE_HISTORY_COLUMNS)
    return f"""
insert into public.{line_history_table} ({columns})
select {columns}
from ufc_odds_line_history_stage
on conflict ({LINE_ON_CONFLICT}) do update set
    event_raw = excluded.event_raw,
    event_url = excluded.event_url,
    odds_american = excluded.odds_american,
    last_seen_at = excluded.last_seen_at,
    last_source_file = excluded.last_source_file,
    updated_at = now();
""".strip()


def render_line_load_sql(part_paths, line_history_table=DEFAULT_LINE_HISTORY_TABLE):
    lines = [
        "\\set ON_ERROR_STOP on",
        "\\timing on",
        "set statement_timeout = '0';",
        "",
    ]
    columns = ", ".join(LINE_HISTORY_COLUMNS)
    for index, part_path in enumerate(part_paths, start=1):
        path = Path(part_path).resolve()
        lines.extend(
            [
                f"\\echo Loading compact odds line history part {index}/{len(part_paths)}: {path.name}",
                "begin;",
                line_stage_table_sql(),
                f"\\copy ufc_odds_line_history_stage ({columns}) from {sql_literal(path)} with (format csv, header true)",
                upsert_line_history_sql(line_history_table),
                "commit;",
                "",
            ]
        )
    lines.extend([f"analyze public.{line_history_table};", ""])
    return "\n".join(lines)


def render_line_verify_sql(manifest, line_history_table=DEFAULT_LINE_HISTORY_TABLE):
    return f"""
\\set ON_ERROR_STOP on
\\timing on

select
    count(*)::bigint as segment_rows,
    min(valid_from) as min_valid_from,
    max(last_seen_at) as max_last_seen_at,
    count(distinct first_source_file)::bigint as first_source_files,
    count(distinct last_source_file)::bigint as last_source_files
from public.{line_history_table};

select
    {int(manifest["input_row_count"])}::bigint as compiled_input_rows,
    {int(manifest["segment_row_count"])}::bigint as compiled_segment_rows,
    {float(manifest["compression_ratio"])}::numeric as compiled_compression_ratio;
""".lstrip()


def close_compact_segment(writer, segment):
    writer.write_row(segment)


def line_history_key(segment):
    return tuple(segment.get(column, "") for column in LINE_ON_CONFLICT.split(","))


def compile_compact_bulk_import(
    data_dir=DEFAULT_DATA_DIR,
    output_dir=DEFAULT_OUTPUT_DIR,
    rows_per_file=1_000_000,
    limit_files=None,
    progress_every=250,
    overwrite=False,
):
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    ensure_output_dir(output_dir, overwrite=overwrite)
    csv_paths = find_all_csvs(data_dir)
    if limit_files is not None:
        csv_paths = csv_paths[:limit_files]
    if not csv_paths:
        raise RuntimeError(f"No ufc_odds_fightoddsio_*.csv files found in {data_dir}")

    writer = ChunkedCsvWriter(
        output_dir,
        rows_per_file,
        columns=LINE_HISTORY_COLUMNS,
        part_prefix=LINE_PART_PREFIX,
    )
    active_segments = {}
    segment_keys = set()
    skipped_files = []
    input_row_count = 0
    duplicate_input_key_count = 0
    duplicate_key_count = 0
    changed_quote_count = 0
    unchanged_quote_count = 0
    disappeared_quote_count = 0
    processed_file_count = 0
    min_scraped_at = None
    max_scraped_at = None

    def close_segment(segment):
        nonlocal duplicate_key_count
        key = line_history_key(segment)
        if key in segment_keys:
            duplicate_key_count += 1
            return
        segment_keys.add(key)
        close_compact_segment(writer, segment)

    try:
        for index, csv_path in enumerate(csv_paths, start=1):
            file_keys = set()
            file_rows = 0
            seen_keys = set()
            try:
                for row in iter_rows_from_csv(csv_path):
                    history_row_key = history_key(row)
                    if history_row_key in file_keys:
                        duplicate_input_key_count += 1
                        continue
                    file_keys.add(history_row_key)

                    key = line_key(row)
                    seen_keys.add(key)
                    active = active_segments.get(key)
                    if active is None:
                        active_segments[key] = line_segment_from_row(row)
                    elif int(active["odds_american"]) == int(row["odds_american"]):
                        active["last_seen_at"] = row["scraped_at"]
                        active["last_source_file"] = row["source_file"]
                        active["event_raw"] = row.get("event_raw")
                        active["event_url"] = row.get("event_url")
                        unchanged_quote_count += 1
                    else:
                        close_segment(active)
                        active_segments[key] = line_segment_from_row(row)
                        changed_quote_count += 1

                    input_row_count += 1
                    file_rows += 1
                    scraped_at = row.get("scraped_at")
                    if scraped_at:
                        min_scraped_at = scraped_at if min_scraped_at is None else min(min_scraped_at, scraped_at)
                        max_scraped_at = scraped_at if max_scraped_at is None else max(max_scraped_at, scraped_at)

                for missing_key in sorted(set(active_segments) - seen_keys):
                    close_segment(active_segments.pop(missing_key))
                    disappeared_quote_count += 1

                processed_file_count += 1
                if progress_every and (index == 1 or index % progress_every == 0 or index == len(csv_paths)):
                    print(
                        json.dumps(
                            {
                                "status": "compiled_compact_file",
                                "index": index,
                                "total_files": len(csv_paths),
                                "source_file": csv_path.name,
                                "file_rows": file_rows,
                                "input_rows": input_row_count,
                                "segment_rows": writer.total_rows,
                                "active_segments": len(active_segments),
                                "parts": len(writer.part_paths),
                            }
                        ),
                        flush=True,
                    )
            except pd.errors.EmptyDataError:
                skipped_files.append({"csv_path": str(csv_path), "reason": "empty_csv"})
            except pd.errors.ParserError as exc:
                skipped_files.append({"csv_path": str(csv_path), "reason": f"parser_error: {exc}"})
    finally:
        for key in sorted(active_segments):
            close_segment(active_segments[key])
        writer.close()

    segment_row_count = writer.total_rows
    compression_ratio = round(input_row_count / segment_row_count, 4) if segment_row_count else 0
    manifest = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": "compact",
        "data_dir": str(data_dir.resolve()),
        "output_dir": str(output_dir.resolve()),
        "source_file_count": len(csv_paths),
        "processed_file_count": processed_file_count,
        "skipped_file_count": len(skipped_files),
        "skipped_files": skipped_files,
        "input_row_count": input_row_count,
        "segment_row_count": segment_row_count,
        "compression_ratio": compression_ratio,
        "changed_quote_count": changed_quote_count,
        "unchanged_quote_count": unchanged_quote_count,
        "disappeared_quote_count": disappeared_quote_count,
        "duplicate_input_key_count": duplicate_input_key_count,
        "duplicate_key_count": duplicate_key_count,
        "rows_per_file": rows_per_file,
        "part_count": len(writer.part_paths),
        "part_files": [str(path.resolve()) for path in writer.part_paths],
        "min_scraped_at": min_scraped_at,
        "max_scraped_at": max_scraped_at,
        "line_history_table": DEFAULT_LINE_HISTORY_TABLE,
    }

    manifest_path = output_dir / LINE_MANIFEST_NAME
    load_sql_path = output_dir / LINE_LOAD_SQL_NAME
    verify_sql_path = output_dir / LINE_VERIFY_SQL_NAME
    load_sql_path.write_text(render_line_load_sql(writer.part_paths), encoding="utf-8")
    verify_sql_path.write_text(render_line_verify_sql(manifest), encoding="utf-8")

    manifest["manifest_path"] = str(manifest_path.resolve())
    manifest["load_sql_path"] = str(load_sql_path.resolve())
    manifest["verify_sql_path"] = str(verify_sql_path.resolve())
    manifest["load_command"] = (
        f"psql \"$SUPABASE_DB_URL\" -v ON_ERROR_STOP=1 -f "
        f"{shlex.quote(str(load_sql_path.resolve()))}"
    )
    manifest["verify_command"] = (
        f"psql \"$SUPABASE_DB_URL\" -v ON_ERROR_STOP=1 -f "
        f"{shlex.quote(str(verify_sql_path.resolve()))}"
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def compile_bulk_import(
    data_dir=DEFAULT_DATA_DIR,
    output_dir=DEFAULT_OUTPUT_DIR,
    rows_per_file=1_000_000,
    limit_files=None,
    sample_fight_count=5,
    progress_every=250,
    overwrite=False,
):
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    ensure_output_dir(output_dir, overwrite=overwrite)
    csv_paths = find_all_csvs(data_dir)
    if limit_files is not None:
        csv_paths = csv_paths[:limit_files]
    if not csv_paths:
        raise RuntimeError(f"No ufc_odds_fightoddsio_*.csv files found in {data_dir}")

    writer = ChunkedCsvWriter(output_dir, rows_per_file)
    skipped_files = []
    matchup_stats = {}
    matchup_index = {}
    total_rows = 0
    duplicate_key_count = 0
    processed_file_count = 0
    min_scraped_at = None
    max_scraped_at = None

    try:
        for index, csv_path in enumerate(csv_paths, start=1):
            file_keys = set()
            file_rows = 0
            try:
                update_matchup_stats_from_csv(matchup_stats, matchup_index, csv_path)
                for row in iter_rows_from_csv(csv_path):
                    key = history_key(row)
                    if key in file_keys:
                        duplicate_key_count += 1
                        continue
                    file_keys.add(key)
                    writer.write_row(row)
                    update_matchup_row_count(matchup_index, row)
                    total_rows += 1
                    file_rows += 1
                    scraped_at = row.get("scraped_at")
                    if scraped_at:
                        min_scraped_at = (
                            scraped_at if min_scraped_at is None else min(min_scraped_at, scraped_at)
                        )
                        max_scraped_at = (
                            scraped_at if max_scraped_at is None else max(max_scraped_at, scraped_at)
                        )
                processed_file_count += 1
                if progress_every and (index == 1 or index % progress_every == 0 or index == len(csv_paths)):
                    print(
                        json.dumps(
                            {
                                "status": "compiled_file",
                                "index": index,
                                "total_files": len(csv_paths),
                                "source_file": csv_path.name,
                                "file_rows": file_rows,
                                "compiled_rows": total_rows,
                                "parts": len(writer.part_paths),
                            }
                        ),
                        flush=True,
                    )
            except pd.errors.EmptyDataError:
                skipped_files.append({"csv_path": str(csv_path), "reason": "empty_csv"})
            except pd.errors.ParserError as exc:
                skipped_files.append({"csv_path": str(csv_path), "reason": f"parser_error: {exc}"})
    finally:
        writer.close()

    manifest = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "data_dir": str(data_dir.resolve()),
        "output_dir": str(output_dir.resolve()),
        "source_file_count": len(csv_paths),
        "processed_file_count": processed_file_count,
        "skipped_file_count": len(skipped_files),
        "skipped_files": skipped_files,
        "compiled_row_count": total_rows,
        "duplicate_key_count": duplicate_key_count,
        "rows_per_file": rows_per_file,
        "part_count": len(writer.part_paths),
        "part_files": [str(path.resolve()) for path in writer.part_paths],
        "min_scraped_at": min_scraped_at,
        "max_scraped_at": max_scraped_at,
        "history_table": DEFAULT_HISTORY_TABLE,
        "ingest_table": DEFAULT_INGEST_TABLE,
        "matchup_samples": summarize_matchup_samples(matchup_stats, sample_fight_count),
    }

    manifest_path = output_dir / MANIFEST_NAME
    load_sql_path = output_dir / LOAD_SQL_NAME
    verify_sql_path = output_dir / VERIFY_SQL_NAME
    load_sql_path.write_text(render_load_sql(writer.part_paths), encoding="utf-8")
    verify_sql_path.write_text(render_verify_sql(manifest), encoding="utf-8")

    manifest["manifest_path"] = str(manifest_path.resolve())
    manifest["load_sql_path"] = str(load_sql_path.resolve())
    manifest["verify_sql_path"] = str(verify_sql_path.resolve())
    manifest["load_command"] = (
        f"psql \"$SUPABASE_DB_URL\" -v ON_ERROR_STOP=1 -f "
        f"{shlex.quote(str(load_sql_path.resolve()))}"
    )
    manifest["verify_command"] = (
        f"psql \"$SUPABASE_DB_URL\" -v ON_ERROR_STOP=1 -f "
        f"{shlex.quote(str(verify_sql_path.resolve()))}"
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compile FightOdds CSV history into psql COPY files and verification SQL."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--rows-per-file", type=int, default=1_000_000)
    parser.add_argument("--limit-files", type=int)
    parser.add_argument("--sample-fights", type=int, default=5)
    parser.add_argument("--progress-every", type=int, default=250)
    parser.add_argument("--mode", choices=["compact", "snapshot"], default="compact")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.mode == "compact":
            manifest = compile_compact_bulk_import(
                data_dir=args.data_dir,
                output_dir=args.output_dir,
                rows_per_file=args.rows_per_file,
                limit_files=args.limit_files,
                progress_every=args.progress_every,
                overwrite=args.overwrite,
            )
        else:
            manifest = compile_bulk_import(
                data_dir=args.data_dir,
                output_dir=args.output_dir,
                rows_per_file=args.rows_per_file,
                limit_files=args.limit_files,
                sample_fight_count=args.sample_fights,
                progress_every=args.progress_every,
                overwrite=args.overwrite,
            )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

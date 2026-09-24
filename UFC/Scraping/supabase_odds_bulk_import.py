import argparse
import csv
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from supabase_odds_publisher import (
    DEFAULT_DATA_DIR,
    DEFAULT_LINE_HISTORY_TABLE,
    LINE_ON_CONFLICT,
    find_all_csvs,
    history_key,
    iter_rows_from_csv,
    line_key,
    line_segment_from_row,
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
SNAPSHOT_BULK_IMPORT_RETIRED = (
    "Snapshot bulk import to ufc_odds_history is retired. "
    "Use --mode compact to compile ufc_odds_line_history."
)
LINE_HISTORY_COLUMNS = [
    "source",
    "market",
    "event_name",
    "fight_id",
    "source_event_id",
    "event_raw",
    "event_url",
    "fighter",
    "source_fighter_id",
    "sherdog_fighter_id",
    "fighter_identity_key",
    "sportsbook",
    "odds_american",
    "valid_from",
    "last_seen_at",
    "first_source_file",
    "last_source_file",
]


class ChunkedCsvWriter:
    def __init__(self, output_dir, rows_per_file, columns=None, part_prefix=LINE_PART_PREFIX):
        if rows_per_file < 1:
            raise ValueError("--rows-per-file must be at least 1")
        self.output_dir = Path(output_dir)
        self.rows_per_file = rows_per_file
        self.columns = columns or LINE_HISTORY_COLUMNS
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


def line_stage_table_sql():
    return """
create temp table ufc_odds_line_history_stage (
    source text not null,
    market text not null,
    event_name text not null,
    fight_id text not null default '',
    source_event_id text,
    event_raw text,
    event_url text,
    fighter text not null,
    source_fighter_id text,
    sherdog_fighter_id bigint,
    fighter_identity_key text,
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
    source_event_id = excluded.source_event_id,
    source_fighter_id = excluded.source_fighter_id,
    sherdog_fighter_id = excluded.sherdog_fighter_id,
    fighter_identity_key = excluded.fighter_identity_key,
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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compile FightOdds CSV snapshots into compact line-history psql COPY files."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--rows-per-file", type=int, default=1_000_000)
    parser.add_argument("--limit-files", type=int)
    parser.add_argument("--progress-every", type=int, default=250)
    parser.add_argument("--mode", choices=["compact", "snapshot"], default="compact")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    if args.mode == "snapshot":
        raise SystemExit(SNAPSHOT_BULK_IMPORT_RETIRED)

    try:
        manifest = compile_compact_bulk_import(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            rows_per_file=args.rows_per_file,
            limit_files=args.limit_files,
            progress_every=args.progress_every,
            overwrite=args.overwrite,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

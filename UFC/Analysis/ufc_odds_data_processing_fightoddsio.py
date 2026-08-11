#!/usr/bin/env python3

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path


FILE_PATTERN = re.compile(r"ufc_odds_fightoddsio_(\d{8}_\d{4})\.csv")
FIELDNAMES = [
    "file1",
    "file2",
    "fighter",
    "sportsbook",
    "odds_before",
    "odds_after",
]
STATE_VERSION = 1


class ProcessingError(RuntimeError):
    pass


def load_files(directory: Path) -> list[str]:
    if not directory.is_dir():
        raise ProcessingError(f"Source directory does not exist: {directory}")

    files = [entry.name for entry in directory.iterdir() if FILE_PATTERN.fullmatch(entry.name)]
    files.sort(key=lambda name: FILE_PATTERN.fullmatch(name).group(1))
    if not files:
        raise ProcessingError(f"No UFC odds snapshots found in {directory}")
    return files


def read_snapshot(path: Path) -> list[dict[str, str]]:
    if path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file, strict=True)
        if not reader.fieldnames or "Fighters" not in reader.fieldnames:
            raise ProcessingError(f"Snapshot is missing the Fighters column: {path}")
        if any(not fieldname for fieldname in reader.fieldnames):
            raise ProcessingError(f"Snapshot contains an empty header: {path}")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ProcessingError(f"Snapshot contains duplicate headers: {path}")

        rows = []
        try:
            for row_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise ProcessingError(f"Snapshot has a ragged row at {path}:{row_number}")
                rows.append(row)
        except csv.Error as error:
            raise ProcessingError(f"Malformed CSV snapshot {path}: {error}") from error
        return rows


def detect_odds_movement(
    odds_before: list[dict[str, str]], odds_after: list[dict[str, str]]
) -> list[dict[str, str]]:
    movements = []
    for fighter_before, fighter_after in zip(odds_before, odds_after):
        if fighter_before["Fighters"] != fighter_after["Fighters"]:
            continue
        for sportsbook in fighter_before:
            if sportsbook in ("Fighters", "Event"):
                continue
            if (
                sportsbook in fighter_after
                and fighter_before[sportsbook]
                and fighter_after[sportsbook]
                and fighter_before[sportsbook] != fighter_after[sportsbook]
            ):
                movements.append(
                    {
                        "fighter": fighter_before["Fighters"],
                        "sportsbook": sportsbook,
                        "odds_before": fighter_before[sportsbook],
                        "odds_after": fighter_after[sportsbook],
                    }
                )
    return movements


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata_digest(directory: Path, files: list[str]) -> str:
    digest = hashlib.sha256()
    for name in files:
        stat_result = (directory / name).stat()
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat_result.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(stat_result.st_mtime_ns).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def write_state_atomic(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as state_file:
            json.dump(state, state_file, indent=2, sort_keys=True)
            state_file.write("\n")
            state_file.flush()
            os.fsync(state_file.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def build_state(source: Path, files: list[str], output: Path) -> dict[str, object]:
    return {
        "version": STATE_VERSION,
        "last_snapshot": files[-1],
        "processed_snapshot_count": len(files),
        "prefix_metadata_sha256": metadata_digest(source, files),
        "output_sha256": file_sha256(output),
    }


def validate_state_schema(state: object) -> dict[str, object]:
    if not isinstance(state, dict):
        raise ProcessingError("Checkpoint must contain a JSON object; run with --full-rebuild")
    if state.get("version") != STATE_VERSION or isinstance(state.get("version"), bool):
        raise ProcessingError("Unsupported checkpoint version; run with --full-rebuild")

    count = state.get("processed_snapshot_count")
    last_snapshot = state.get("last_snapshot")
    prefix_digest = state.get("prefix_metadata_sha256")
    output_digest = state.get("output_sha256")
    digest_pattern = re.compile(r"[0-9a-f]{64}")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ProcessingError("Invalid processed snapshot count; run with --full-rebuild")
    if not isinstance(last_snapshot, str) or not FILE_PATTERN.fullmatch(last_snapshot):
        raise ProcessingError("Invalid last snapshot in checkpoint; run with --full-rebuild")
    if not isinstance(prefix_digest, str) or not digest_pattern.fullmatch(prefix_digest):
        raise ProcessingError("Invalid snapshot digest in checkpoint; run with --full-rebuild")
    if not isinstance(output_digest, str) or not digest_pattern.fullmatch(output_digest):
        raise ProcessingError("Invalid output digest in checkpoint; run with --full-rebuild")
    return state


def load_and_validate_state(
    state_path: Path, output: Path, source: Path, files: list[str]
) -> dict[str, object]:
    if not state_path.is_file() or not output.is_file():
        raise ProcessingError("Output or checkpoint is missing; run with --full-rebuild")

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProcessingError(f"Cannot read checkpoint {state_path}: {error}") from error

    state = validate_state_schema(state)

    count = state.get("processed_snapshot_count")
    last_snapshot = state.get("last_snapshot")
    if count > len(files):
        raise ProcessingError("Invalid processed snapshot count; run with --full-rebuild")
    if files[count - 1] != last_snapshot:
        raise ProcessingError("Snapshot history changed before the checkpoint; run with --full-rebuild")
    if metadata_digest(source, files[:count]) != state.get("prefix_metadata_sha256"):
        raise ProcessingError("Processed snapshot metadata changed; run with --full-rebuild")
    if file_sha256(output) != state.get("output_sha256"):
        raise ProcessingError("Movement output changed after checkpointing; run with --full-rebuild")
    return state


def write_pair_movements(
    writer: csv.DictWriter,
    file1: str,
    file2: str,
    odds_before: list[dict[str, str]],
    odds_after: list[dict[str, str]],
) -> int:
    count = 0
    for movement in detect_odds_movement(odds_before, odds_after):
        writer.writerow(
            {
                "file1": file1,
                "file2": file2,
                **movement,
            }
        )
        count += 1
    return count


def full_rebuild(source: Path, files: list[str], output: Path) -> tuple[Path, int, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    output_mode = stat.S_IMODE(output.stat().st_mode) if output.exists() else 0o644
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    temporary_path = Path(temporary_name)
    movement_count = 0
    try:
        os.fchmod(descriptor, output_mode)
        with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=FIELDNAMES)
            writer.writeheader()
            previous_name = files[0]
            previous_rows = read_snapshot(source / previous_name)
            for current_name in files[1:]:
                current_rows = read_snapshot(source / current_name)
                movement_count += write_pair_movements(
                    writer,
                    previous_name,
                    current_name,
                    previous_rows,
                    current_rows,
                )
                previous_name = current_name
                previous_rows = current_rows
            output_file.flush()
            os.fsync(output_file.fileno())
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return temporary_path, len(files) - 1, movement_count


def incremental_update(
    source: Path,
    files: list[str],
    output: Path,
    processed_count: int,
) -> tuple[Path | None, int, int]:
    new_files = files[processed_count:]
    if not new_files:
        return None, 0, 0

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    movement_count = 0
    try:
        shutil.copyfile(output, temporary_path)
        shutil.copymode(output, temporary_path)
        previous_name = files[processed_count - 1]
        previous_rows = read_snapshot(source / previous_name)
        with temporary_path.open("a", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=FIELDNAMES)
            for current_name in new_files:
                current_rows = read_snapshot(source / current_name)
                movement_count += write_pair_movements(
                    writer,
                    previous_name,
                    current_name,
                    previous_rows,
                    current_rows,
                )
                previous_name = current_name
                previous_rows = current_rows
            output_file.flush()
            os.fsync(output_file.fileno())
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return temporary_path, len(new_files), movement_count


def transaction_path_for(state_path: Path) -> Path:
    return state_path.with_name(f".{state_path.name}.transaction.json")


def discard_transaction(output: Path, state_path: Path) -> None:
    transaction_path = transaction_path_for(state_path)
    if not transaction_path.is_file():
        return
    temporary_path = None
    try:
        transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
        if not isinstance(transaction, dict) or transaction.get("version") != STATE_VERSION:
            raise ProcessingError("Invalid transaction")
        transaction_state = validate_state_schema(transaction.get("state"))
        temporary_name = transaction.get("temporary_output")
        if isinstance(temporary_name, str):
            candidate = Path(temporary_name)
            if (
                candidate.parent.resolve() == output.parent.resolve()
                and candidate.name.startswith(f".{output.name}.")
                and candidate.is_file()
                and file_sha256(candidate) == transaction_state["output_sha256"]
            ):
                temporary_path = candidate
    except (OSError, json.JSONDecodeError, ProcessingError):
        pass
    if temporary_path is not None:
        temporary_path.unlink(missing_ok=True)
    transaction_path.unlink(missing_ok=True)


def recover_transaction(output: Path, state_path: Path) -> None:
    transaction_path = transaction_path_for(state_path)
    if not transaction_path.is_file():
        return
    try:
        transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProcessingError(f"Cannot recover transaction {transaction_path}: {error}") from error
    if not isinstance(transaction, dict) or transaction.get("version") != STATE_VERSION:
        raise ProcessingError(f"Invalid processing transaction: {transaction_path}")

    new_state = validate_state_schema(transaction.get("state"))
    temporary_name = transaction.get("temporary_output")
    if not isinstance(temporary_name, str):
        raise ProcessingError(f"Invalid processing transaction: {transaction_path}")
    temporary_path = Path(temporary_name)
    expected_parent = output.parent.resolve()
    if (
        temporary_path.parent.resolve() != expected_parent
        or not temporary_path.name.startswith(f".{output.name}.")
    ):
        raise ProcessingError(f"Unsafe temporary output in transaction: {transaction_path}")

    expected_sha = str(new_state["output_sha256"])
    if output.is_file() and file_sha256(output) == expected_sha:
        if temporary_path.is_file() and file_sha256(temporary_path) == expected_sha:
            temporary_path.unlink()
    elif temporary_path.is_file() and file_sha256(temporary_path) == expected_sha:
        os.replace(temporary_path, output)
    else:
        raise ProcessingError(f"Cannot recover processing transaction: {transaction_path}")

    write_state_atomic(state_path, new_state)
    transaction_path.unlink()


def commit_artifacts(
    temporary_output: Path,
    output: Path,
    state_path: Path,
    new_state: dict[str, object],
) -> None:
    transaction_path = transaction_path_for(state_path)
    transaction = {
        "version": STATE_VERSION,
        "temporary_output": str(temporary_output.resolve()),
        "state": new_state,
    }
    write_state_atomic(transaction_path, transaction)
    os.replace(temporary_output, output)
    write_state_atomic(state_path, new_state)
    transaction_path.unlink()


def process(
    source: Path,
    output: Path,
    state_path: Path,
    force_full_rebuild: bool = False,
) -> dict[str, object]:
    if force_full_rebuild:
        discard_transaction(output, state_path)
    else:
        recover_transaction(output, state_path)
    files = load_files(source)
    bootstrap = not output.is_file() and not state_path.is_file()

    if force_full_rebuild:
        temporary_output, pairs_processed, movements_written = full_rebuild(source, files, output)
        mode = "full"
    elif bootstrap:
        temporary_output, pairs_processed, movements_written = full_rebuild(source, files, output)
        mode = "full"
    else:
        state = load_and_validate_state(state_path, output, source, files)
        processed_count = int(state["processed_snapshot_count"])
        temporary_output, pairs_processed, movements_written = incremental_update(
            source, files, output, processed_count
        )
        mode = "incremental"
        if pairs_processed == 0:
            return {
                "mode": mode,
                "snapshots": len(files),
                "pairs_processed": 0,
                "movements_written": 0,
                "output_sha256": state["output_sha256"],
                "last_snapshot": state["last_snapshot"],
            }

    transaction_path = transaction_path_for(state_path)
    try:
        state = build_state(source, files, temporary_output)
        commit_artifacts(temporary_output, output, state_path, state)
    except BaseException:
        if not transaction_path.exists():
            temporary_output.unlink(missing_ok=True)
        raise
    return {
        "mode": mode,
        "snapshots": len(files),
        "pairs_processed": pairs_processed,
        "movements_written": movements_written,
        "output_sha256": state["output_sha256"],
        "last_snapshot": state["last_snapshot"],
    }


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Build UFC line movement data incrementally")
    parser.add_argument(
        "--source",
        type=Path,
        default=script_dir.parent / "Scraping" / "data",
        help="Directory containing timestamped UFC odds snapshots",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / "data" / "ufc_odds_movements_fightoddsio.csv",
        help="Movement CSV output path",
    )
    parser.add_argument(
        "--state",
        type=Path,
        help="Checkpoint JSON path (defaults beside the output)",
    )
    parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Ignore any checkpoint and rebuild the complete movement CSV",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    state_path = (
        args.state.expanduser().resolve()
        if args.state
        else Path(f"{output}.state.json")
    )
    if state_path == output:
        print("State and output paths must be different", file=sys.stderr)
        return 2

    try:
        result = process(source, output, state_path, args.full_rebuild)
    except (OSError, csv.Error, ProcessingError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        "Odds processing complete: "
        f"mode={result['mode']} "
        f"snapshots={result['snapshots']} "
        f"pairs_processed={result['pairs_processed']} "
        f"movements_written={result['movements_written']} "
        f"last_snapshot={result['last_snapshot']} "
        f"sha256={result['output_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

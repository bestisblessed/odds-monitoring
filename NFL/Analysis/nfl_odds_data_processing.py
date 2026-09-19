import argparse
import csv
import glob
import json
import os
import re
import shutil
from datetime import datetime, timedelta

import pandas as pd


RAW_PATTERN = re.compile(r"nfl_odds_vsin_\d{8}_\d{4}\.json$")
IGNORED_COLUMNS = {"SPR", "ML", "TOT"}
BOOK_NAMES = {"CIRCA": "Circa", "CAESARS": "Caesars", "BETMGM": "BetMGM", "DK": "DK"}


def load_files(directory):
    files = sorted(
        (name for name in os.listdir(directory) if RAW_PATTERN.match(name)),
        key=lambda name: re.findall(r"(\d{8}_\d{4})", name)[0],
    )
    return files


def _compact(value):
    return " ".join(str(value or "").split())


def _time_from_marker(value):
    match = re.search(r"(\d{1,2}:\d{2}\s*[AP]M(?:\s+ET)?)", str(value), re.I)
    return _compact(match.group(1)) if match else None


def _game_key(game_date, game_time, team1, team2):
    teams = tuple(sorted((_compact(team1).casefold(), _compact(team2).casefold())))
    return (_compact(game_date).casefold(), _compact(game_time).casefold(), *teams)


def _normalize_triplets(snapshot):
    games = {}
    index = 0
    while index + 2 < len(snapshot):
        marker, team1_row, team2_row = snapshot[index:index + 3]
        if not marker:
            index += 1
            continue
        date_column = next(iter(marker))
        game_time = _time_from_marker(marker.get(date_column))
        team1 = _compact(team1_row.get(date_column))
        team2 = _compact(team2_row.get(date_column))
        if not game_time or not team1 or not team2 or _time_from_marker(team1) or _time_from_marker(team2):
            index += 1
            continue
        quotes = {}
        for source in set(team1_row).intersection(team2_row):
            if source == date_column or source in IGNORED_COLUMNS or source.startswith("Column"):
                continue
            before, after = _compact(team1_row.get(source)), _compact(team2_row.get(source))
            if before or after:
                quotes[BOOK_NAMES.get(source, source.title())] = f"{before} | {after}"
        games[_game_key(date_column, game_time, team1, team2)] = {
            "game_date": date_column, "game_time": game_time,
            "team1": team1, "team2": team2, "quotes": quotes,
        }
        index += 3
    return games


def _normalize_legacy(snapshot):
    games = {}
    for row in snapshot:
        time_key = next((key for key in row if str(key).strip().casefold() == "time"), None)
        if time_key is None:
            continue
        game_time = _compact(row.get(time_key))
        date_column = next((key for key in row if key != time_key), None)
        if not date_column:
            continue
        teams = [part.strip() for part in str(row.get(date_column, "")).split("\n") if part.strip()]
        if len(teams) < 2:
            continue
        team1, team2 = teams[0], teams[-1]
        quotes = {
            BOOK_NAMES.get(key, str(key).title()): str(value).replace("\n", " | ")
            for key, value in row.items()
            if key not in {time_key, date_column} and value not in (None, "")
        }
        games[_game_key(date_column, game_time, team1, team2)] = {
            "game_date": date_column, "game_time": game_time,
            "team1": team1, "team2": team2, "quotes": quotes,
        }
    return games


def normalize_snapshot(snapshot):
    """Normalize legacy game objects and current time/team/team triplets."""
    legacy = _normalize_legacy(snapshot)
    return legacy if legacy else _normalize_triplets(snapshot)


def detect_odds_movement(odds_before, odds_after):
    before_games = normalize_snapshot(odds_before)
    after_games = normalize_snapshot(odds_after)
    movements = []
    quote_changes = 0
    for identity in sorted(set(before_games).intersection(after_games)):
        before, after = before_games[identity], after_games[identity]
        for sportsbook in sorted(set(before["quotes"]).intersection(after["quotes"])):
            old, new = before["quotes"][sportsbook], after["quotes"][sportsbook]
            if old != new:
                quote_changes += 1
                movements.append({
                    "game_date": before["game_date"], "game_time": before["game_time"],
                    "team1": before["team1"], "team2": before["team2"],
                    "sportsbook": sportsbook, "odds_before": old, "odds_after": new,
                })
    if quote_changes and not movements:
        raise RuntimeError(f"Detected {quote_changes} parseable quote changes but generated zero movement rows")
    return movements


def extract_timestamp(filename):
    try:
        return datetime.strptime("_".join(filename.removesuffix(".json").split("_")[-2:]), "%Y%m%d_%H%M")
    except ValueError:
        return None


def process_directory(directory, output_path):
    files = load_files(directory)
    rows = []
    normalized_games = 0
    for file1, file2 in zip(files, files[1:]):
        with open(os.path.join(directory, file1)) as f1, open(os.path.join(directory, file2)) as f2:
            before, after = json.load(f1), json.load(f2)
        normalized_games += len(normalize_snapshot(before)) + len(normalize_snapshot(after))
        for movement in detect_odds_movement(before, after):
            rows.append({
                "file1": file1, "file2": file2,
                "game_date": movement["game_date"], "game_time": movement["game_time"],
                "matchup": f"{movement['team1']} vs {movement['team2']}",
                "sportsbook": movement["sportsbook"],
                "odds_before": movement["odds_before"], "odds_after": movement["odds_after"],
            })
    if len(files) > 1 and normalized_games == 0:
        raise RuntimeError("No games could be parsed from the supplied odds snapshots")
    base_columns = ["file1", "file2", "game_date", "game_time", "matchup", "sportsbook", "odds_before", "odds_after"]
    frame = pd.DataFrame(rows, columns=base_columns)
    if not frame.empty:
        frame[["team_1", "team_2"]] = frame["matchup"].str.split(" vs ", n=1, expand=True)
        frame[["team1_odds_before", "team2_odds_before"]] = frame["odds_before"].str.split(r"\s+\|\s+", n=1, expand=True)
        frame[["team1_odds_after", "team2_odds_after"]] = frame["odds_after"].str.split(r"\s+\|\s+", n=1, expand=True)
        for column in ["team1_odds_before", "team2_odds_before", "team1_odds_after", "team2_odds_after"]:
            frame[column] = frame[column].str.split().str[0]
        frame["time_before"] = frame["file1"].map(extract_timestamp).map(lambda dt: dt.strftime("%b %d %-I:%M%p") if dt else None)
        frame["time_after"] = frame["file2"].map(extract_timestamp).map(lambda dt: dt.strftime("%b %d %-I:%M%p") if dt else None)
    else:
        for column in ["team_1", "team_2", "team1_odds_before", "team2_odds_before", "team1_odds_after", "team2_odds_after", "time_before", "time_after"]:
            frame[column] = pd.Series(dtype="object")
    frame = frame.map(lambda value: value.strip() if isinstance(value, str) else value)
    frame.to_csv(output_path, index=False)
    frame.loc[frame["sportsbook"].eq("Circa")].to_csv(output_path.replace(".csv", "_circa.csv"), index=False)
    frame.loc[frame["sportsbook"].eq("DK")].to_csv(output_path.replace(".csv", "_dk.csv"), index=False)
    print(f"Parsed {normalized_games} game snapshots and wrote {len(frame)} movement rows to {output_path}")
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="../Scraping/data")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    os.makedirs(args.data_dir, exist_ok=True)
    if os.path.isdir(args.source_dir):
        shutil.copytree(args.source_dir, args.data_dir, dirs_exist_ok=True)
    odds_dir = os.path.join(args.data_dir, "odds")
    for path in glob.glob(os.path.join(odds_dir, "*")):
        if os.path.isfile(path) and os.stat(path).st_size == 0:
            os.remove(path)
    output = os.path.join(args.data_dir, "nfl_odds_movements.csv")
    frame = process_directory(odds_dir, output)

    default_start = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    start_date = args.start_date or input(f"Enter start date (YYYYMMDD) [press Enter for {default_start}]: ").strip() or default_start
    default_end = (datetime.strptime(start_date, "%Y%m%d") + timedelta(days=7)).strftime("%Y%m%d")
    end_date = args.end_date or input(f"Enter end date (YYYYMMDD) [press Enter for {default_end}]: ").strip() or default_end
    datetime.strptime(start_date, "%Y%m%d"); datetime.strptime(end_date, "%Y%m%d")
    for suffix in ["", "_circa", "_dk"]:
        path = output.replace(".csv", f"{suffix}.csv")
        subset = pd.read_csv(path)
        dates = subset["file1"].str.extract(r"(\d{8})", expand=False)
        subset = subset.loc[dates.between(start_date, end_date)]
        subset.to_csv(path, index=False)
        print(f"Filtered {suffix or 'all'} odds data saved to {path} ({len(subset)} rows)")
    cleanup = args.cleanup or (not args.start_date and input("Remove raw odds files outside the date range? (y/n) [press Enter for n]: ").strip().lower() == "y")
    if cleanup:
        for path in glob.glob(os.path.join(odds_dir, "nfl_odds_vsin_*.json")):
            file_date = os.path.basename(path).split("_")[-2]
            if not start_date <= file_date <= end_date:
                os.remove(path)


if __name__ == "__main__":
    main()

#!/bin/bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_SOURCE="durrrrr:/home/durrrrr/odds-monitoring/UFC/Scraping/data/"
DATA_DIR="$ROOT/UFC/Scraping/data"
OUTPUT="$ROOT/UFC/Analysis/data/ufc_odds_movements_fightoddsio.csv"
STATE=""
FULL_REBUILD=0
LOCAL_ONLY=0
TOTAL_START=$SECONDS

usage() {
    cat <<'EOF'
Usage: ./update_ufc_data.sh [options]

Options:
  --sync-source SOURCE  Rsync source directory (default: durrrrr UFC data)
  --data-dir PATH       Local raw snapshot mirror
  --output PATH         Generated movement CSV
  --state PATH          Incremental checkpoint JSON
  --full-rebuild        Rebuild movements from every snapshot
  --local-only          Skip Streamlit, Swift, and DonPablo delivery
  -h, --help            Show this help
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

require_value() {
    [[ $# -ge 2 && -n "$2" && "$2" != -* ]] || die "$1 requires a value"
}

phase_done() {
    local name="$1"
    local started="$2"
    echo "TIMING: $name=$((SECONDS - started))s"
}

sha256_file() {
    shasum -a 256 "$1" | awk '{print $1}'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sync-source)
            require_value "$@"
            SYNC_SOURCE="$2"
            shift 2
            ;;
        --data-dir)
            require_value "$@"
            DATA_DIR="$2"
            shift 2
            ;;
        --output)
            require_value "$@"
            OUTPUT="$2"
            shift 2
            ;;
        --state)
            require_value "$@"
            STATE="$2"
            shift 2
            ;;
        --full-rebuild)
            FULL_REBUILD=1
            shift
            ;;
        --local-only)
            LOCAL_ONLY=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
done

[[ "$SYNC_SOURCE" != -* ]] || die "Sync source cannot begin with '-'"
[[ -n "$DATA_DIR" && -n "$OUTPUT" ]] || die "Data and output paths cannot be empty"

DATA_DIR="${DATA_DIR%/}"
SYNC_SOURCE="${SYNC_SOURCE%/}/"
if [[ -z "$STATE" ]]; then
    STATE="${OUTPUT}.state.json"
fi
[[ "$STATE" != "$OUTPUT" ]] || die "State and output paths must be different"

if [[ "$SYNC_SOURCE" != *:* ]]; then
    [[ -d "${SYNC_SOURCE%/}" ]] || die "Local sync source does not exist: ${SYNC_SOURCE%/}"
fi

mkdir -p "$DATA_DIR" "$(dirname "$OUTPUT")" "$(dirname "$STATE")"

echo "Syncing UFC snapshots without deleting local history..."
sync_started=$SECONDS
rsync -a \
    --delay-updates \
    --stats \
    --include='ufc_odds_fightoddsio_*.csv' \
    --exclude='*' \
    "$SYNC_SOURCE" "$DATA_DIR/"
phase_done "sync" "$sync_started"

snapshot_count=$(find "$DATA_DIR" -maxdepth 1 -type f -name 'ufc_odds_fightoddsio_*.csv' | wc -l | tr -d ' ')
[[ "$snapshot_count" -gt 0 ]] || die "No UFC odds snapshots were synchronized"
latest_snapshot=$(find "$DATA_DIR" -maxdepth 1 -type f -name 'ufc_odds_fightoddsio_*.csv' -print | sort | tail -1)
[[ -s "$latest_snapshot" ]] || die "Latest UFC odds snapshot is empty: $latest_snapshot"
latest_header=$(LC_ALL=C sed -n '1{s/\r$//;p;}' "$latest_snapshot")
[[ "$latest_header" == *Fighters* ]] || die "Latest snapshot is missing the Fighters header: $latest_snapshot"
echo "Validated snapshots: count=$snapshot_count latest=$(basename "$latest_snapshot")"

processor_started=$SECONDS
processor_args=(
    "$ROOT/UFC/Analysis/ufc_odds_data_processing_fightoddsio.py"
    --source "$DATA_DIR"
    --output "$OUTPUT"
    --state "$STATE"
)
if [[ "$FULL_REBUILD" -eq 1 ]]; then
    processor_args+=(--full-rebuild)
fi
python "${processor_args[@]}"
phase_done "processing" "$processor_started"

[[ -s "$OUTPUT" ]] || die "Movement output was not created: $OUTPUT"
expected_header='file1,file2,fighter,sportsbook,odds_before,odds_after'
output_header=$(LC_ALL=C sed -n '1{s/\r$//;p;}' "$OUTPUT")
[[ "$output_header" == "$expected_header" ]] || die "Movement output has an unexpected header"
[[ -s "$STATE" ]] || die "Processing checkpoint was not created: $STATE"
output_sha=$(sha256_file "$OUTPUT")
echo "Validated output: rows=$(wc -l < "$OUTPUT" | tr -d ' ') sha256=$output_sha"

if [[ "$LOCAL_ONLY" -eq 1 ]]; then
    echo "Local-only mode: skipped Streamlit, Swift, and DonPablo delivery"
else
    delivery_started=$SECONDS
    streamlit_target="/Users/td/Code/mma-ai/Streamlit/data/ufc_odds_movements_fightoddsio.csv"
    swift_target="/Users/td/Code/mma-ai-swift-app/data/ufc_odds_movements_fightoddsio.csv"
    remote_target="/Users/pablo/Code/mma-ai-swift-app/data/ufc_odds_movements_fightoddsio.csv"
    [[ -d "$(dirname "$streamlit_target")" ]] || die "Streamlit data directory is missing"
    [[ -d "$(dirname "$swift_target")" ]] || die "Swift data directory is missing"

    cp "$OUTPUT" "$streamlit_target"
    cp "$OUTPUT" "$swift_target"
    [[ "$(sha256_file "$streamlit_target")" == "$output_sha" ]] || die "Streamlit checksum mismatch"
    [[ "$(sha256_file "$swift_target")" == "$output_sha" ]] || die "Swift checksum mismatch"

    echo "Copying to Swift app server..."
    scp "$OUTPUT" "donpablo:$remote_target"
    remote_sha=$(ssh donpablo "shasum -a 256 '$remote_target' | awk '{print \$1}'")
    [[ "$remote_sha" == "$output_sha" ]] || die "DonPablo checksum mismatch"
    phase_done "delivery" "$delivery_started"
fi

echo "TIMING: total=$((SECONDS - TOTAL_START))s"

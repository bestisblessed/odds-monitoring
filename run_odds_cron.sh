#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$ROOT/scripts/odds_runtime.sh"
case "${1:-}" in
    nfl) runner="$ROOT/NFL/run_scraper.sh" ;;
    mma) runner="$ROOT/UFC/run_scraper_and_monitor.sh" ;;
    *) echo "Usage: $0 nfl|mma" >&2; exit 2 ;;
esac
# fcntl locks work on both macOS and Linux and release even after a crash.
exec "$PYTHON" - "$ROOT" "$1" "$runner" <<'LOCK'
import fcntl
import os
from pathlib import Path
import subprocess
import sys
root, job, runner = sys.argv[1:]
lock_dir = Path(root) / '.run'
lock_dir.mkdir(exist_ok=True)
with (lock_dir / (job + '.lock')).open('a') as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f'SKIP: {job} odds job is already running', flush=True)
        raise SystemExit(0)
    raise SystemExit(subprocess.call(['/bin/bash', runner], cwd=root, env=os.environ))
LOCK

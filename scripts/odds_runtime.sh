#!/bin/bash
# Shared interpreter for scheduled scrapes and interactive odds refreshes.
ODDS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
if [[ -z "${PYTHON:-}" ]]; then
    if [[ -x "$ODDS_ROOT/.venv/bin/python" ]]; then
        PYTHON="$ODDS_ROOT/.venv/bin/python"
    elif [[ -x "$HOME/.pyenv/shims/python" ]]; then
        PYTHON="$HOME/.pyenv/shims/python"
    else
        PYTHON="$(command -v python3)"
    fi
fi
export PYTHON
export SE_CACHE_PATH="$ODDS_ROOT/.cache/selenium"
# DonPablo is the collector; other Macs pull its archive during weekly refresh.
if [[ -z "${ODDS_SOURCE_ROOT:-}" ]]; then
    if [[ "$(hostname -s)" == "DonPabloMBP" ]]; then
        ODDS_SOURCE_ROOT="$ODDS_ROOT"
    else
        ODDS_SOURCE_ROOT="donpablo:/Users/pablo/Code/odds-monitoring"
    fi
fi
ODDS_SOURCE_ROOT="${ODDS_SOURCE_ROOT%/}"
export ODDS_SOURCE_ROOT

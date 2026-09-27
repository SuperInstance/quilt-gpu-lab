#!/usr/bin/env bash
# run.sh — one cron tick: claim the next experiment, run it under the guard,
# log it. Exits 0 always (breaches are recorded in RESULTS.md, not raised).
set -u
cd "$(dirname "$0")"
exec "$HOME/venvs/elephant-gpu/bin/python" runner.py

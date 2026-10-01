#!/usr/bin/env bash
# c1b_finish.sh — wait for the C1b run to end, then finalize receipts + adjudicate.
set -u
cd /home/eileen/projects/quilt-gpu-lab
RUNPID=1875507
OUT=results/c1_playtest/c1b_run
while kill -0 "$RUNPID" 2>/dev/null; do sleep 30; done
{
  echo "C1B_RUN_END $(date -Is)"
  echo "--- driver.log tail ---"
  tail -25 "$OUT/driver.log" 2>/dev/null
  echo "--- guard dir ---"
  ls -la "$OUT/guard" 2>/dev/null
} > "$OUT/WAITER.done" 2>&1
python3 experiments/c1b_adjudicate.py > "$OUT/c1b_adjudication.json" 2> "$OUT/c1b_adjudication.err" || true
python3 experiments/c1b_book.py >> "$OUT/c1b_adjudication.err" 2>&1 || true
echo "FINISH_JOB_DONE $(date -Is)"

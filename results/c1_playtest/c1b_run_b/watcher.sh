#!/usr/bin/env bash
# watcher.sh — C1b r2 auto-finish: wait for the guarded run outer process to exit,
# then run the FINAL union adjudication + book C1B-RESULTS-ENTRY.md automatically.
set -u
cd /home/eileen/projects/quilt-gpu-lab
OUT=results/c1_playtest/c1b_run_b
OUTER=1890871
while kill -0 "$OUTER" 2>/dev/null; do sleep 20; done
{
  echo "OUTER_EXIT $(date -Is)"
  echo "--- driver.log tail ---"
  tail -40 "$OUT/driver.log" 2>/dev/null
  echo "--- out dir ---"
  ls -la "$OUT"
  echo "--- guard dir ---"
  ls -la "$OUT/guard" 2>/dev/null
} > "$OUT/FINISH.done" 2>&1
sleep 15
{
  echo "--- finalize $(date -Is) ---"
  python3 experiments/c1b_finalize.py
  echo "FINALIZE_RC=$?"
  echo "FINALIZE_DONE $(date -Is)"
} >> "$OUT/FINISH.done" 2>&1

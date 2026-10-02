#!/usr/bin/env bash
# monitor.sh — C1b run progress probe (games.jsonl last game index/tick + wall clock)
set -u
OUT=/home/eileen/projects/quilt-gpu-lab/results/c1_playtest/c1b_run_b
GJ=$OUT/games.jsonl
MON=$OUT/monitor.log
while true; do
  ts=$(date -Is)
  if [ -f "$GJ" ]; then
    last=$(tail -1 "$GJ" 2>/dev/null)
    sz=$(stat -c %s "$GJ" 2>/dev/null)
  else
    last=""; sz=0
  fi
  free=$(/usr/lib/wsl/lib/nvidia-smi --query-gpu=memory.free --format=csv,noheader 2>/dev/null | tr -d ' ')
  alive=$(pgrep -f 'c1_playtest_pong.py --inner' | tr '\n' ',')
  printf '%s sz=%s free=%s inner=%s last=%s\n' "$ts" "$sz" "$free" "$alive" "$last" >> "$MON"
  if [ -z "$alive" ]; then
    echo "$ts INNER_EXITED" >> "$MON"
    break
  fi
  sleep 60
done

#!/bin/bash
# Overnight GPU queue — serial, chip_route-gated, lock-disciplined. 2026-09-28.
# Casey: "go all night with projects and experiments on the metal."
# Storm-proof: pure bash + python, no API dependency.
LAB=/home/eileen/projects/quilt-gpu-lab
PY=/home/eileen/venvs/elephant-gpu/bin/python
LOG=/tmp/overnight_gpu.log
cd "$LAB" || exit 1
ts() { date +%H:%M:%S; }
echo "[$(ts)] overnight queue start" >> "$LOG"

acquire() {
  python3 tools/chip_route.py --class tensor > /tmp/cr.env 2>/tmp/cr.err
  local rc=$?
  if [ $rc -ne 0 ]; then echo "[$(ts)] chip_route REFUSED (rc=$rc): $(cat /tmp/cr.err)" >> "$LOG"; return 1; fi
  . /tmp/cr.env
  echo $$ > .gpu.lock
  return 0
}
release() { rm -f .gpu.lock; }

# ---- Item 1: K2 — real-video (lavfi) replication of K1 --------------------
if [ ! -f training/keel_k1/results/k2_results.json ]; then
  if acquire; then
    echo "[$(ts)] K2 fire (cache lavfi + run)" >> "$LOG"
    K1_SOURCE=lavfi "$PY" training/keel_k1/k1_cache.py >> "$LOG" 2>&1
    rc1=$?
    if [ $rc1 -eq 0 ]; then
      K1_SOURCE=lavfi K1_CACHE=training/keel_k1/cache_lavfi.pt K1_NAME=K2 \
        K1_OUT=training/keel_k1/results/k2_results.json \
        "$PY" training/keel_k1/k1_run.py >> "$LOG" 2>&1
      echo "[$(ts)] K2 run rc=$?" >> "$LOG"
    else
      echo "[$(ts)] K2 CACHE FAILED rc=$rc1" >> "$LOG"
    fi
    release
  fi
else
  echo "[$(ts)] K2 already booked, skipping" >> "$LOG"
fi

# ---- Items 2+: the runner's queue (unchecked experiments), serial ----------
# runner.py carries its own chip_route gate + lock + receipt discipline now.
for i in 1 2 3 4; do
  sleep 20
  if [ -f .gpu.lock ]; then echo "[$(ts)] lock held by sibling, waiting" >> "$LOG"; sleep 120; fi
  echo "[$(ts)] runner pass $i" >> "$LOG"
  python3 runner.py >> "$LOG" 2>&1
  echo "[$(ts)] runner pass $i rc=$?" >> "$LOG"
done

echo "[$(ts)] overnight queue end (gpu-lab-tick cron takes watch from here)" >> "$LOG"

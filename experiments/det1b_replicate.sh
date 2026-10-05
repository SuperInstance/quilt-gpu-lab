#!/bin/bash
# DET-1b seed-replicate driver — prereg: proposals/runs/DET-1b-rest-em-seed-replicate-prereg.md
# 3 seeds x {T, C2}. Heldout FROZEN 20261003. Isolated outputs under results/det1b/.
set -u
cd /home/eileen/projects/quilt-gpu-lab
PY=/home/eileen/venvs/elephant-gpu/bin/python
LOG=results/det1b/det1b.log
COMMON="--difficulty hard --rounds 3 --train-pool 96 --heldout 96 --n-cand 8 --max-steps 150 --device cuda --skip-ollama"
mkdir -p results/det1b
echo "=== DET-1b START $(date -Is) ===" >> $LOG

for SEED in 20261005 20261006 20261007; do
  echo "=== seed=$SEED ARM T $(date -Is) ===" >> $LOG
  $PY experiments/rest_em_loop.py --arm treatment --seed $SEED --seed-heldout 20261003 \
      $COMMON --adapter-dir results/det1b/adapter_s${SEED}_T \
      --out-json results/det1b/rest_em_s${SEED}_T.json >> $LOG 2>&1
  echo "=== seed=$SEED ARM T rc=$? $(date -Is) ===" >> $LOG

  C2STEPS=$($PY -c "
import json
try:
    d = json.load(open('results/det1b/rest_em_s${SEED}_T.json'))
    print(int(d['rounds'][0]['train']['steps']))
except Exception:
    print(150)
" 2>/dev/null)
  echo "=== seed=$SEED ARM C2 (steps=$C2STEPS) $(date -Is) ===" >> $LOG
  $PY experiments/rest_em_loop.py --arm c2 --seed $SEED --seed-heldout 20261003 --c2-steps "$C2STEPS" \
      $COMMON --adapter-dir results/det1b/adapter_s${SEED}_C2 \
      --out-json results/det1b/rest_em_s${SEED}_C2.json >> $LOG 2>&1
  echo "=== seed=$SEED ARM C2 rc=$? $(date -Is) ===" >> $LOG
done
echo "=== DET-1b ALL DONE $(date -Is) ===" >> $LOG

#!/bin/bash
# DET-1c REMEDY driver — prereg: proposals/runs/DET-1c-rest-em-remedy-prereg.md
# Same as det1b_replicate.sh + --exclude-heldout (contamination by construction)
# + pre-fire VRAM gate (>=3.0 GiB free). Outputs under results/det1c/.
set -u
cd /home/eileen/projects/quilt-gpu-lab
PY=/home/eileen/venvs/elephant-gpu/bin/python
LOG=results/det1c/det1c.log
COMMON="--difficulty hard --rounds 3 --train-pool 96 --heldout 96 --n-cand 8 --max-steps 150 --device cuda --skip-ollama --exclude-heldout"
mkdir -p results/det1c

FREE=$($PY -c "import torch; f,_=torch.cuda.mem_get_info(); print(int(f/2**30*10))")
if [ "$FREE" -lt 30 ]; then
  echo "=== DET-1c DEFERRED $(date -Is): free=${FREE}0MiB < 3.0GiB pre-fire gate ===" >> $LOG
  exit 2
fi
echo "=== DET-1c START $(date -Is) free=${FREE}0MiB ===" >> $LOG

for SEED in 20261005 20261006 20261007; do
  echo "=== seed=$SEED ARM T $(date -Is) ===" >> $LOG
  $PY experiments/rest_em_loop.py --arm treatment --seed $SEED --seed-heldout 20261003 \
      $COMMON --adapter-dir results/det1c/adapter_s${SEED}_T \
      --out-json results/det1c/rest_em_s${SEED}_T.json >> $LOG 2>&1
  echo "=== seed=$SEED ARM T rc=$? $(date -Is) ===" >> $LOG

  C2STEPS=$($PY -c "
import json
try:
    d = json.load(open('results/det1c/rest_em_s${SEED}_T.json'))
    print(int(d['rounds'][0]['train']['steps']))
except Exception:
    print(150)
" 2>/dev/null)
  echo "=== seed=$SEED ARM C2 (steps=$C2STEPS) $(date -Is) ===" >> $LOG
  $PY experiments/rest_em_loop.py --arm c2 --seed $SEED --seed-heldout 20261003 --c2-steps "$C2STEPS" \
      $COMMON --adapter-dir results/det1c/adapter_s${SEED}_C2 \
      --out-json results/det1c/rest_em_s${SEED}_C2.json >> $LOG 2>&1
  echo "=== seed=$SEED ARM C2 rc=$? $(date -Is) ===" >> $LOG
done
echo "=== DET-1c ALL DONE $(date -Is) ===" >> $LOG

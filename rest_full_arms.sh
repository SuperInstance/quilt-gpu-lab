#!/bin/bash
# REST-EM-001 full run, Amendment A1 (hard distribution) — 4 arms, separate fresh processes.
# prereg: proposals/runs/REST-EM-prereg.md (frozen) + A1. Keeper: Lucineer. 2026-10-02 02:0x AKDT.
cd /home/eileen/projects/quilt-gpu-lab
PY=/home/eileen/venvs/elephant-gpu/bin/python
LOG=results/rest_em_full.log
COMMON="--difficulty hard --rounds 3 --train-pool 96 --heldout 96 --n-cand 8 --max-steps 150 --device cuda --skip-ollama"
mkdir -p results
echo "=== FULL RUN START $(date -Is) | A1 hard distribution, 4 fresh-process arms (T/C1/C2/N2), round-0 via HF (--skip-ollama logged as deviation per post-smoke annotation 3) ===" >> $LOG

echo "=== ARM T (treatment) $(date -Is) ===" >> $LOG
$PY experiments/rest_em_loop.py --arm treatment $COMMON --out-json results/rest_em_full_T.json >> $LOG 2>&1
T_RC=$?
echo "=== ARM T done rc=$T_RC $(date -Is) ===" >> $LOG

echo "=== ARM C1 (no-finetune) $(date -Is) ===" >> $LOG
$PY experiments/rest_em_loop.py --arm c1 $COMMON --out-json results/rest_em_full_C1.json >> $LOG 2>&1
echo "=== ARM C1 done rc=$? $(date -Is) ===" >> $LOG

# C2 budget matched to treatment round-1 actual optimizer steps (prereg section 6)
C2STEPS=$($PY -c "
import json
try:
    d = json.load(open('results/rest_em_full_T.json'))
    print(int(d['rounds'][0]['train']['steps']))
except Exception:
    print(150)
" 2>/dev/null)
echo "=== ARM C2 (oracle-SFT 48 demos, steps=$C2STEPS) $(date -Is) ===" >> $LOG
$PY experiments/rest_em_loop.py --arm c2 $COMMON --c2-steps "$C2STEPS" --out-json results/rest_em_full_C2.json >> $LOG 2>&1
echo "=== ARM C2 done rc=$? $(date -Is) ===" >> $LOG

echo "=== ARM N2 (shuffle-label control, 30 steps) $(date -Is) ===" >> $LOG
$PY experiments/rest_em_loop.py --arm n2 $COMMON --out-json results/rest_em_full_N2.json >> $LOG 2>&1
echo "=== ARM N2 done rc=$? $(date -Is) ===" >> $LOG

echo "=== ALL ARMS COMPLETE $(date -Is) ===" >> $LOG

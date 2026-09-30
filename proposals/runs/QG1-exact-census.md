# QG1 — exact-census re-read of exp022 (2026-09-29, pre-registered)

## Question
exp020–022's census runs at 512 shots. Shot noise at n=512 is ±0.044 (95% CI half-width).
Does the desert structure (bar 0.45, break cells 0.498 train-visible, k4 near-miss 0.418) survive when every
recorded genome is re-evaluated with EXACT statevector probabilities (no sampling)?

## Method (frozen before run)
Torch CUDA statevector sim, n_qubits=3, |000> init, gate set {h,x,rx(θ),cx,swap} as 8x8 complex matrices,
bit order q0=MSB (target indices 0=000, 7=111), p_target = |s000|²+|s111|².
Corpus: every cell in receipts/exp022-desert-break/exp022.telemetry.{k3,k4,k5,k6,k7}.jsonl (60 gens x 16 cells = 960 genome-evals).

## Anchor (fail-loud, must hold before gates are read)
ANCHOR: >=99% of recorded train_p/verify_p values lie within 0.044 of my exact p.
If anchor fails: simulator semantics wrong -> STOP, diagnose, never re-roll blind.

## Gates (frozen)
- G1 HIDDEN_CROSSERS == 0: no cell with recorded verify < 0.45 has true p >= 0.45 (the desert is real, not shot noise).
- G2 k4_near_miss_confirmed: k4's recorded champion (0.418) has true p < 0.45.
- G3 break_cells_at_ceiling: mean true p of in_band cells >= 0.48 (GHZ ceiling ~0.5).
- EXPLORATORY (labeled, not gates): loneliness gap (top1 - top2 true p per gen); ancestry of break cells
  (first-gen appearance + min replace/indel edit distance to any earlier-gen cell -> is the break one edit away?).

## Why GPU
The whole census = one batched matmul chain on the 4050; scales to QG2 (4096 salted streams, live evolution)
which is the follow-up if G1–G3 hold.

# DET-1b — REST-EM seed-replicate (remedy for DET-1 tranche-1 RED row)

- Spawned by: DET-1 determinism census (commit 094d2bd, RED row: REST-EM full arms are
  single-draw torch/qlora runs with no nondeterminism receipt).
- Producing harness: `experiments/rest_em_loop.py` (committed 416ca8c lane). Arms replicated:
  **T** (treatment, 3-cycle policy self-training) and **C2** (oracle-SFT, budget-matched).
  C1 is NOT replicated: it is an eval-pipeline stability receipt (Δ0.000) and eval is greedy.
- Booked result under test: T Δ−0.0729 (declined), C2 Δ−0.125 (hurt), vs base pass@1 0.6875
  on the frozen hard heldout (RESULTS.md "REST-EM FULL ARMS", booked 12:2x Oct 4).

## Frozen configuration
- Seeds: {20261005, 20261006, 20261007} via `--seed` (varies training draw: task pool,
  mutation/shuffle, torch init noise path).
- HELDOUT FROZEN: `--seed-heldout 20261003` (identical eval set as booking — we vary the
  training draw only; base 0.6875 is the shared comparator).
- Per-seed flags identical to booked run: `--difficulty hard --rounds 3 --train-pool 96
  --heldout 96 --n-cand 8 --max-steps 150 --device cuda --skip-ollama`.
- C2 steps budget-matched to that seed's T round-1 actual steps (same rule as booked run).
- Outputs isolated: `results/det1b/rest_em_s{seed}_{T|C2}.json`,
  `results/det1b/adapter_s{seed}_{T|C2}_r*`. Booked artifacts untouched.
- GPU context at pre-reg: foreign idle server.py processes hold ~2.5 GiB (0% util); ~3.6 GiB
  free; nf4 0.5B lane fits. Serial: no other lab lane fires during this run.

## Gates (pre-registered, words)
- **G1 (run validity)**: every arm×seed run reaches rc=0 with verifier selftest PASS; any
  crash = fix-in-place declared pre-verdict (committed), else STOP.
- **G2 (measurement)**: per-seed Δ = (arm final heldout pass@1) − (that arm's own round-0
  base pass@1 at same seed). Base drift across seeds is reported, not gated.
- **G3 (verdict — the remedy gate)**:
  - If **either** T or C2 has a Δ **sign flip in ≥1 of 3 seeds** → the original booking
    DOWNGRADES to: "direction unstable at N=1 seeds; margin < seed noise" (amendment in
    place, original text preserved).
  - If signs are **stable across all 3 seeds for both arms** → original booking UPGRADES
    to determinism class (b) seeded-ensemble; margins restated as mean Δ over 4 draws
    (booked + 3).
- **G4 (discipline)**: single firing, no re-rolls; partial completion books honestly as
  partial. Results booked in RESULTS.md with a QUEUE mark; manifest re-sealed after landing.

## Cost estimate
~2h wall (6 arms ≈ 25–30 min each on the 4050), disk ~2 GiB adapters (pruned to r2 only if
space tight — declared if so).

Fired only after this file is committed+pushed.

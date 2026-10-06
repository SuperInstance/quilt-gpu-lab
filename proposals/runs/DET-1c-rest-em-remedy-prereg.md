# DET-1c — REST-EM seed-replicate, REMEDY FIRING (contamination-by-construction + VRAM plan)

- Spawned by: DET-1b BOOKED ABORTED-PARTIAL (RESULTS.md 15:1x Oct 5; pre-reg 38d6ea3).
  DET-1b's abort gates worked fail-loud but the DESIGN was flawed: pool seeding was only
  CHECKED against the frozen heldout post-hoc; 2 of 3 seeds collided (overlap=1 task each).
  One arm OOM'd (T, round-0 SFT backward, 914 MB alloc vs free 0) with foreign lanes
  holding ~2.5 GiB.
- Same booked result under test as DET-1b (unchanged): REST-EM FULL ARMS T Δ−0.0729 /
  C2 Δ−0.125 vs base 0.6875 (RESULTS.md 12:2x Oct 4); DET-1 tranche-1 RED row (single-draw,
  no nondeterminism receipt). This firing is the owed REMEDY — not a re-roll: DET-1b never
  delivered G3-usable data (1/6 arms completed), and every fix below was declared HERE
  before firing, per DET-1b G4.

## Fix 1 — contamination excluded BY CONSTRUCTION (not checked post-hoc)
- `experiments/rest_em_loop.py` gains `gen_task_pool_excluding(...)` + `--exclude-heldout`
  flag: the train pool is generated deterministically (same rng seed, family rotation)
  while SKIPPING any candidate whose `task.expr` appears in the frozen heldout's expr set,
  continuing the rotation until counts fill. Two independent calls are byte-identical
  (smoke-tested pre-commit for all 3 seeds: overlap=0, deterministic=True, pool=96).
- The legacy N4 contamination check remains downstream and still exits 2 on any overlap —
  it is now a redundant witness, not the only line of defense.
- DECLARED DEVIATION: the exclusion builder interleaves family draws (two-phase order in
  the legacy builder cannot "continue" cleanly past a skip), so even a clean seed gets a
  different-but-equally-distributed pool vs the booked run. Family mix may deviate from
  exact rotation when a collision is skipped (skipped count logged + booked). This does
  not touch any gate word: gates operate on Δ per seed, not on pool composition.
- Honest note: skipped=0 for seeds 20261006/20261007 under the NEW rng stream (they
  collide only under the LEGACY stream). The builder is the declared object of test.

## Fix 2 — VRAM headroom plan (declared pre-fire, no mid-run protocol change)
- Batch/accum params stay IDENTICAL to the booked run (batch 4, accum 2) — no re-roll
  territory touched.
- Pre-fire gate: `torch.cuda.mem_get_info()` must show ≥ 3.0 GiB free at firing (at
  pre-reg time: 4.95 GiB; foreign lanes lighter than at DET-1b). If < 3.0 GiB at fire
  time, do not fire; book the deferral.
- If OOM recurs despite this: it is a G1 crash, booked honestly (STOP, no fix-in-place
  that changes batch/pool). Foreign server.py lanes are Casey's — never killed.

## Frozen configuration (identical to DET-1b except --exclude-heldout)
- Seeds: {20261005, 20261006, 20261007}. HELDOUT FROZEN: `--seed-heldout 20261003`.
- Flags: `--difficulty hard --rounds 3 --train-pool 96 --heldout 96 --n-cand 8
  --max-steps 150 --device cuda --skip-ollama --exclude-heldout`.
- C2 steps budget-matched to that seed's T round-1 actual steps (same rule as booked run).
- Outputs isolated: `results/det1c/rest_em_s{seed}_{T|C2}.json` + adapters. results/det1b/
  untouched (archive-never-delete).

## Gates (pre-registered, words — same as DET-1b, unchanged)
- **G1 (run validity)**: every arm×seed run reaches rc=0 with verifier selftest PASS; any
  crash = STOP and book honestly (crash is a verdict, not something to fix mid-run).
- **G2 (measurement)**: per-seed Δ = (arm final heldout pass@1) − (that arm's own round-0
  base pass@1 at same seed). Base drift across seeds is reported, not gated.
- **G3 (verdict — the remedy gate)**:
  - Either arm with a Δ **sign flip in ≥1 of 3 completed seeds** → original booking
    DOWNGRADES to "direction unstable at N=1 seeds; margin < seed noise" (amendment in
    place, original preserved).
  - Both arms sign-stable across all 3 completed seeds → original booking UPGRADES to
    determinism class (b) seeded-ensemble; margins restated as mean Δ over 4 draws.
  - If <3 seeds complete for an arm → G3 UNDETERMINABLE for that arm; book partial; the
    remedy remains OWED (a future firing may only proceed under a NEW pre-reg).
- **G4 (discipline)**: single firing, no re-rolls. Results booked in RESULTS.md with a
  QUEUE mark; manifest re-sealed after landing (blocked while the foreign d12u4 lane
  persists — book the refusal if it still stands).

## Cost estimate
~1.5–2 h wall (6 arms; DET-1b's surviving arm ran 15 min; collision-free pools may run
longer). Disk ~2 GiB adapters. Serial: no other lab lane fires during this run.

Fired only after this file + the producing code are committed+pushed.

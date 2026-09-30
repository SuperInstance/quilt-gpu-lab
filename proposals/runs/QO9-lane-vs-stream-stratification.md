# QO9 (AMENDED) — where does the oracle signal live: stream or lane?

AMENDMENT 1 (2026-09-30 14:1x AKDT, day-conductor): the original draft said "existing data,
CPU ~30m". **That premise is FALSE** — no prior lane (QO1/QO3/QG3/QG6/QG7) persisted per-stream
per-gen features; every booking saved aggregates only. Stratification requires a fresh
multi-lane per-stream dump. This pre-reg replaces the draft; the draft's gates are preserved
in spirit (0.60 / 0.80 thresholds) and restated below.

## Question
SCOUT-5/SCOUT-6 CONTRADICT-candidate (jev-fusion steelman pt 3 + projection law): a per-stream
sparse signal cannot represent GROUPED error. QO5 proved all streams in a lane share one
skeleton draw; the per-lane variable is the mutation-draw seed. If the gen-1 oracle signal is
lane-idiosyncratic (memorizes the mutation draw) rather than stream-level, the QO2 routing law
(oracle at gen 1, AUC 0.88) and QO6's per-stream kill evidence inherit a grouped-error caveat.

## Design
- K=4 lanes, mutation-draw seeds {1234, 1235, 1236, 1237}; S=1024 streams/lane; GENS=12;
  SHOTS/BAR/pipeline VERBATIM from experiments/qo3_horizon.py (qg2_scale_lane primitives,
  skeleton_seqs deterministic — identical skeleton in all lanes, as in every prior booking).
- Persist per-stream gen-1..3 features + outcome `crossed` + lane id IN the artifact
  (RC-1 doctrine: real-set membership recorded in the result file).
- Metrics (MLP, QO3-identical architecture/optimizer, stream-level 80/20 split inside the
  training lanes):
  - pooled AUC(g1): train/test mixed across lanes (matches all prior bookings' regime);
  - lane-held-out AUC(g1): train on 3 lanes, test on the 4th, rotated over all 4 folds.
- Seed: torch.manual_seed(0) per fit; numpy rngs seeded per lane; no re-roll on gate miss.

## Gates (frozen, in words)
- P1 (stream-level stands): lane-held-out AUC(g1) >= 0.80 on ALL 4 folds → jev-fusion
  objection answered for this substrate; QO3/QO6/QO7 bookings untouched.
- P2 (grouped-error caveat): lane-held-out AUC(g1) < 0.60 on ALL 4 folds while pooled
  AUC(g1) >= 0.80 → signal is lane-level; QO2/QO6 gain a booked grouped-error caveat;
  per-stream kill evidence downgraded to lane-level evidence; spawn QO9b.
- MIXED / intermediate (any fold in [0.60, 0.80), or folds straddling the boundary):
  verdict INCONCLUSIVE — book the band, no architectural claim either way.
- G1 fail-loud: any lane with crossing rate outside [0.50, 0.65] → FAILED-DIVERGED, abort,
  book the failure (lane anchor vs recorded QG2 band ~0.58 at S=4096; looser band at S=1024).

## Threats this booking (name them before fire)
- Threatens: QO3 horizon (AUC 0.880 at g1), QO6 gate (per-stream e-process evidence),
  QG7 routing law ("forecast for the cross-by-12 majority"), and the QO2 integration item QO7.
- Steelman (ST-STEEL, retro-fit): the strongest case against stream-level signal is QO5's
  birth-lottery finding — g0 is byte-identical across streams, so ALL per-stream signal at g1
  comes from ONE selection round of ONE shared mutation draw; a classifier may be reading
  draw-specific fitness noise. If so, lane-held-out folds collapse while pooled folds shine
  (train/test share the draw) — exactly the P2 signature. This is why the test is worth firing.

## Cost
GPU (RTX 4050, lane free), ~10-15 min: 4 lanes x 1024 x 12 gens rollout + 8 short MLP fits.
Runner: experiments/qo9_lane_vs_stream.py with `--out` (RC-1 fix; scratch verification writes
NEVER into results/). Output embeds runner_sha256 + args + per-lane membership.

## Interpretation rules
STOP after one fire per the frozen gates; mixed results are booked as INCONCLUSIVE, never
re-rolled with new seeds.

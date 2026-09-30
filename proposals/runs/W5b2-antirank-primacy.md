# W5b2 — antirank-primacy confirmation (pre-registration)

**Fired from:** W5b's pre-registered SECONDARY comparison, which won 3/3 seeds (antirank vs random:
+2.5% / +1.65% / +3.0% bpb) while the primary (lifetime vs random) was KILLED (seed-dependent, no
direction). This is a NEW directional hypothesis test informed by a pre-registered secondary — not a
post-hoc rescue of W5b.
**Status:** FROZEN before fire. Machinery identical to W5b (imports the same committed runner module;
no constants changed — only arms, seeds, output dir, and these gates).

## Question
Is precision-on-the-most-flipped (antirank) a stable, reproducible win over random allocation in
from-scratch ternary training — i.e., does *instability* (not memory lifetime) mark which weights
deserve to survive rounding?

## Frozen design
- Identical to W5b (corpus pin, TWN, commit cadence C=25, warmup T=4000, main T=6000, k=2%, lr 3e-3,
  fresh optimizer + identical data order at fork) — see proposals/runs/W5b-lifetime-precision.md.
- **Arms:** `antirank` vs `random` only. **Seeds: 5291, 5292, 5293, 5294, 5295** (fresh, no overlap
  with W5b's 4241-4243).
- Output: `results/w5b2_antirank_primacy/{results.json,run.log}`.

## Gates (frozen — confirmation-grade)
- **KEEP:** mean relative bpb improvement of antirank over random ≥ 0.5% AND antirank beats random in
  ≥ 4/5 seed-pairs.
- **KILL:** otherwise — the 3/3 W5b signal was a small-sample fluke; book both runs together as
  "allocation by delta instability: not reproducible."
- Context booked either way: per-seed margins + the lifetime seed-instability observation from W5b.

## Honest risks
- 2 arms × 5 seeds = 10 arm-runs ≈ 90 min GPU; if the effect is real but <0.5%, KILL is the honest
  booking (we pre-registered the same margin as W5b).
- One corpus, one architecture (GRU-384); KEEP claims "reproducible in OUR regime," not generality.

## Artifacts
`experiments/w5b2_antirank_primacy.py` (imports `w5b_lifetime_precision` machinery),
`results/w5b2_antirank_primacy/{results.json,run.log}`.

# W5b — lifetime-scaled ternary delta state (pre-registration)

**Fired from:** SPOOL wave 6 seed W5b (M11, STEPQuant/LeapQuant convergence: precision allocated by
memory lifetime, never tested in from-scratch ternary training).
**Status:** FROZEN before fire. Any change after fire = amendment, documented in-place, never silent.

## Question
Our free-delta stream is a recurrence; during plain ternary training each weight's committed ternary
state has a measurable lifetime (how often it flips). Does allocating a small high-precision budget to
the **longest-lived** elements yield lower held-out loss (bpb) than allocating the same budget uniformly
or at random — at identical training budget?

## Claim (primary)
Allocating the high-precision slots to the longest-lived delta positions beats random allocation on
held-out bpb at equal budget.

## Frozen design
- **Corpus:** all tracked `*.md` files in quilt-gpu-lab at the fire commit (`git ls-files '*.md'`,
  sorted, concatenated with `\n\n`, UTF-8, capped at 2 MiB). Corpus is pinned by the fire commit hash —
  receipt-clean by construction. Split: first 90% train / final 10% valid (contiguous bytes).
- **Model:** char-level 1-layer GRU, hidden 384, embed 384 (float, excluded from ternary pool),
  linear head. Ternarized pool = GRU `weight_ih_l0`, `weight_hh_l0`, head `weight` (~928k elements).
  Biases + embedding stay float (frozen note: input/output fidelity kept; the pool is the bulk).
- **Ternary convention (TWN, frozen):** per tensor, Δ = 0.7·mean|W|; Q = sign(W) where |W|>Δ else 0;
  s = mean(|W| over |W|>Δ). Forward weight = s·Q + H, where H is nonzero only on high-precision (HP)
  slots: H_i = W_i − s·Q_i at each commit (HP elements are permanently exact). STE: backward treats
  forward weight as W (identity straight-through).
- **Commit cadence:** every C=25 steps, recompute Q, s, H from W (Adam lr 3e-3, grad clip 1.0, batch 64,
  seq 64, no schedule).
- **Lifetime statistic (frozen):** during a shared WARMUP phase (plain ternary, no HP slots),
  T_warm=4000 steps → 160 commits; per-element statistic = **change_count** = number of committed-state
  flips observed during warmup. Arms fork from the identical warmup checkpoint per seed:
  - `lifetime`: HP = k elements with FEWEST flips (longest-lived).
  - `uniform`: HP = deterministic stride `linspace(0, N-1, k)`.
  - `random`: HP = seeded uniform choice without replacement.
  - `antirank` (secondary, exploratory, pre-registered): HP = k elements with MOST flips.
    Purpose: if antirank beats lifetime, the M11 abstraction INVERTS at training time (instability,
    not persistence, marks precision-worthiness) — itself a novel, bookable finding.
- **Budget equality:** k = 2% of pool elements (~18.5k), identical across arms; T_main=6000 steps each;
  identical data order and optimizer seeds per seed; 3 base seeds (4241, 4242, 4243).
- **Metric:** held-out bpb (total NLL bits / valid bytes, full-sequence crops) at T_main end.
  Curve logged every 1000 steps for the receipt.

## Gates (frozen)
- **KEEP (primary):** mean bpb(lifetime) ≤ mean bpb(random) − 0.5% relative AND lifetime beats random
  in ≥2/3 seed-pairs.
- **KILL (primary):** |relative improvement| < 0.5% or wrong direction in ≥2/3 seed-pairs — "lifetime
  structure in the delta stream is real but not exploitable at allocation time" (or absent).
- **Secondary (report, no gate):** antirank vs lifetime vs uniform ordering.

## Honest risks
- 160 warmup commits make change_count coarse (0–160); elements that never flip vs flip-once are
  indistinguishable in rate — accepted, it is the statistic the D-ledger analogy gives us.
- `uniform` stride correlates with tensor layout (row-major); if uniform ≈ lifetime, layout confounds —
  random arm remains the primary comparator, uniform is context.
- Single hardware, single corpus; this tests exploitability in OUR regime, not frontier generality.

## Compute
Single RTX 4050, fp32, ~28k total steps/seed ≈ 25–30 min → ~80–90 min all seeds. Well under the
seed's "overnight" estimate; reported honestly if it lands short.

## Artifacts
`experiments/w5b_lifetime_precision.py`, `results/w5b_lifetime_precision/{results.json,run.log}`.
Booking in RESULTS.md only after `results.json` exists; manifest re-sealed at booking.

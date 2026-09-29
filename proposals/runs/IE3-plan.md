# IE3 — Specialist trunks: sequential specialization vs joint training

**Pre-registered 2026-09-29 13:35 AKDT, before any IE3 run.** Status: scoped
(scope-only session: plan + code + py_compile; NOT fired, no git, no GPU).

## Why

IE2 (KEEP) inverted IE1's caveat: the wide-field pooled correlator DOES carry
small-field direction — a blob-only specialist ridge reads r2 0.541 / 0.806 /
0.930 at densities 8/16/32 where the mixed-trained reader managed 0.061 /
0.044 / 0.015. One reader + one mixed training distribution = dilution. The
crew doctrine in miniature: specialists keep their skill; mixtures lose it.

IE3 prices the next rung of that doctrine at the component level: can ONE
shared trunk serve TWO specialist heads — wide-field (grating) direction and
small-field (blob) direction — without dilution, and does SEQUENTIAL
specialization (blob first, then add the direction head) beat JOINT
multi-task training from step 0? IE2's follow-up note named the shape
("two-head reader, wide-field + small-field"); IE3 fires it as a controlled
3-arm comparison.

## Task definition (frozen)

Both heads decode the true direction unit vector (vx, vy) per frame from the
same IE1/IE2 sensor stream (4 pooled fam codes, τ=2). The **blob head** is
trained and evaluated on blob frames only; the **direction head** on grating
frames only (IE1's primary wide-field task). Heads never cross families in
training — the only shared thing under test is the TRUNK.

## Design (frozen)

Three arms, identical sensor, identical streams, identical eval:

- **A-joint** — one shared trunk; loss = MSE_blob + MSE_dir summed from
  epoch 0. Both heads active throughout.
- **B-sequential** — phase 1: trunk + blob head only (direction head does
  not exist yet), blob-only loss, until blob **val** r2 ≥ **0.40** (min 50
  epochs, cap 400). Then the direction head is created (fresh init) and
  phase 2 trains BOTH losses (consolidation, anti-forgetting) until the
  trunk has seen exactly **600 total epochs** — A's budget, equalized. B's
  direction head gets fewer epochs than A's (600 − p1): if B still wins on
  direction, the claim is conservative.
- **C-split-trunks** — two independent trunk+head specialists, one per
  family, 600 epochs each; the crew-doctrine baseline (IE2's specialist,
  generalized to both families). C pays 2× trunk compute — the doctrine's
  standing cost, booked.

Architecture/hyperparameters (frozen): trunk = Linear 4→12 → tanh →
Linear 12→8 → tanh (164 params); heads = Linear 8→2 (18 params each).
Adam (lr 0.01, β₁ 0.9, β₂ 0.999, eps 1e-8), full-batch, float64. Weight
decay **0.01** on weight matrices only — IE2's ridge α=0.01 carried into
the gradient regime (biases unpenalized, matching IE1's ridge, which
penalizes W only). A closed-form ridge has no training dynamics, so
sequential-vs-joint is undefined for it; the reader class change is the
necessary delta, everything downstream of the sensor is frozen.

Sensor stack = IE2 verbatim (imported from `ie1_reichardt.py`): blob
σ ∈ {2,3}, blob speeds {0.25, 0.5}, 4 cardinals, densities 8/16/32, τ = 2
frames, warmup 12 / kept 48; grating side λ ∈ {8,16} at the same frozen
speeds {0.25, 0.5} — IE1's grating speed 1.0 is DROPPED so both families
share IE2's speed set and balance at 16 cfgs each (2×2×4). Documented
delta, not a silent change.

Standardization (frozen): A/B trunks z-score inputs over the POOLED train
frames of both families (the sharing burden); C specialists z-score over
their own family's train frames (specialists own their preprocessing).

### Seed law (frozen)

Seed base **20260929** (fresh; IE2 used 20260928). Streams follow IE2's law
verbatim: seed = base + 1000·ci + 10·si + split_offset. Blob cfgs ci 0–15
(IE2 enumeration order: σ × v × DIR_ORDER); grating cfgs ci 100–115
(disjoint block — IE1's mixed single enumeration is NOT reused). si 0–2 =
train (offset 0); si 3 = val (offset 0 — B's competence gate ONLY, never in
any gradient); si 0–3 at offset 100 = held-out test, never touched by
training or gates. Model init: one rng per arm × density,
default_rng(base + 500000 + 1000·arm_index + 17·density_index), arms A/B/C
= 0/1/2; fixed draw order (trunk, blob head, direction head — B's direction
head draws at the switch from the same stream). Bit-identical reruns on one
machine.

### Eval protocol (frozen)

Datasets are built ONCE per density and shared (same objects) across all
three arms. Per arm per density: r2_blob (blob head on blob test frames),
r2_direction (direction head on grating test frames), via IE1's r2_multi +
cardinal accuracy. 2304 train / 768 val / 3072 test frames per family per
density, asserted fail-loud.

## Gate (frozen, exact)

Let r2_dir_X[d], r2_blob_X[d] be arm X's test metrics at density d.

1. **SPECIALIZATION_WINS** iff
   r2_dir_B[32] − r2_dir_A[32] ≥ **0.15** AND
   r2_blob_B[32] ≥ r2_blob_C[32] − **0.05**.
2. else **JOINT_OK** iff at EVERY density d ∈ {8, 16, 32}:
   r2_blob_A[d] ≥ max_arms(r2_blob[d]) − **0.05** AND
   r2_dir_A[d] ≥ max_arms(r2_dir[d]) − **0.05**.
3. else **DILUTION_CONFIRMS**.

Precedence 1 → 2 → 3 (mutually exclusive: a B-over-A direction win ≥ 0.15
already denies A within-0.05-of-max on that head). The 0.15 / 0.05 / 0.05
numbers are frozen BEFORE any run; no post-hoc re-reading.

- SPECIALIZATION_WINS → schedule is the cure: one trunk serves both
  specialists, but only when specialized first.
- JOINT_OK → the generalist is viable at this scale: compartmentalized
  heads already prevent IE1-style dilution; schedule irrelevant.
- DILUTION_CONFIRMS → trunk sharing dilutes under BOTH schedules; split
  specialists (C) remain the reader doctrine.

### Fail-loud / INVALID_HARNESS (frozen)

Any of the following poisons the verdict to **INVALID_HARNESS**
(per-density data still booked; no science claim; K3b rule — diagnose,
never re-roll):

- B phase-1 competence (val blob r2 ≥ 0.40) unreached at the 400-epoch cap
  at ANY density. Known risk at density 8 (IE2 ridge test ceiling 0.541;
  the 0.40 gate sits 0.14 under it — deliberately: competence = specialist
  territory, ≫ the diluted 0.061, yet reachable at the hardest density).
- Any non-finite loss or metric (asserted per epoch and at every eval).
- Any dataset shape assertion failure.

## Diagnostics (descriptive, no gates)

- B forgetting: blob val r2 at the switch vs after phase 2.
- Cross-family leakage: each head tested on the OTHER family's test frames
  (does a shared trunk bleed one family into the other head?).
- C vs IE2's ridge ceiling per density (C is the gradient-trained
  restatement of IE2's blob specialist; expected close but not identical —
  different reader class, fresh seed base).
- B's p1_epochs per density (how long specialization takes).

## Artifacts

`experiments/ie3_specialist_trunks.py` · `results/ie3_specialist_trunks.json`
(when fired) · `ie3_run.log` (when fired) · this plan. CPU-only (numpy,
system python3), no GPU lock, minutes-scale.

# SCOUT-11 — SuperInstance push sweep, day conductor (2026-10-01 19:11Z / 11:11 AKDT)
Sweep: recent commits (48h window, since 2026-09-29T19:11Z) on 16 repos + open PRs on 8 active ones. Read-only, nothing filed.

## Classifications

### (TOOL/STEAL) fleet-triage PR #1 — "RTX 4050 worklist: GPU-only work for the fleet's consumer-GPU agent" (updated 18:08Z)
Written FOR us. Two docs:
- `RTX4050-BUILDSPECS.md` A1: pie-minimax nonlinear-closure — MLP 9→64→9 (~1.3k params) on 180,361 exact
  tic-tac-toe labels; pre-registered P1 (global top-1 in [0.25,0.40]) / P2 (COMPOSED/fork states <70% of
  global); reproduce-linear-0.1807-first gate; receipt format given. Follows their Exp 2 (decision-tree
  ceiling) which landed VERIFIED multi-beam at 16:21Z — our FT-1 lane is closed upstream, A1 is the next rung.
- A4/D3: Determinism Lab pre-reg skeleton — where does GPU parallelism break bit-determinism and does chained
  canon hashing detect it (H1 atomics / H2 fp-reorder / H3 canon-safety). Directly serves our lane-torch-
  nondeterminism lesson (QG7: book subpopulation verdicts as rerun ensembles) — this would CONVERT that lesson
  into a measured map. Needs bracket-filling + our own pre-reg before any run.
- Their §0 control rule ("control must vary the audited thing by a DIFFERENT path") already spec-amended into
  ST1-AUDIT by SCOUT-8; the determinism skeleton instantiates it correctly.

### (CORROBORATE/TOOL) fleet-triage 18:59Z — projection-doctrine experiment (results landed)
Measures the fleet slogan "every observation is a projection; no downstream cleverness recovers what the
looking never carried" on connect4 ground truth, observation ladder L0→L5 × 4 learners × 2 splits.
Corroborates two of our bookings from an independent substrate:
- W5a (trace vs fresh at matched budget): their ladder is the systematic version of our finding that the
  fresh-full advantage is bought by budget, not by re-observation.
- QO1/QO3 oracle (cv>v>gen feature projection): same question — how much does a lossy observation ladder
  cost the downstream predictor, and does the answer invert under distribution shift?
Their L1 (colour-collapsed) BEATING L0 (lossless) for logreg under the by-ply shift (0.9202 vs 0.8513) is
the sharpest single number: LESS observation can generalize better across shift. Spawned QO10.

### (TOOL) quilt-research-canons scout 16:28Z — quilt-llvm semantic-mutation lab
1,127 input mutants, 0% killed vs 76/76 tamper control; 113 provably-wrong survivors. Fail-open class
fleet-wide; RAISES our RC-1b (dead-branch census) — a never-executed gate branch is exactly a 0%-killed
mutant population. No new item needed; cite in RC-1b.

### (CORROBORATE) quilt-neighbourhood v0.5/v0.6 (P8 reconciliation events + DID-signed diffs)
Fail-closed applyReconciliation (id gate, parents-known gate, assert-or-rollback) + sig-as-overlay keeping
revisions value-pure. Same doctrine family as our receipt-manifest sealer; nothing to book, nothing
threatened. Note for any future QO7 scoreboard: reconciliation-events-as-DAG-markers is a clean pattern for
booking lineage.

### (state changes already consumed)
delta-shape PR #1 merged 19:31Z (our QO6 already consumes its eproc pin lineage). murmuration's
"GPU experiment brief with decision trees" (23:43Z) is the same doc pattern as fleet-triage's
GPU-EXPERIMENTS — covered by SCOUT-8 doctrine; no new action this wake.

**No CONTRADICT findings this sweep.** Nothing booked in quilt-gpu-lab is threatened by anything pushed
in the last 24h. QC-JEV's dismissal of the murmuration JEV-null remains the freshest threat resolution.

## SPAWNED QUEUE ITEMS
- **[open] FT-A1** (GPU, ~1 evening per their spec, pre-reg FIRST): pie-minimax nonlinear closure exactly per
  fleet-triage PR #1 buildspec. Gate 0: reproduce linear 0.1807 on the baseline harness or STOP (port defect).
  P1 global top-1 [0.25,0.40]; P2 COMPOSED < 70% of global; 3 pinned seeds, receipt format theirs.
  Do-NOT list inherited verbatim (no goalpost migration, no share-less composed numbers, no single-seed claims).
- **[open] FT-D3** (GPU, pre-reg TEMPLATE provided, brackets must be filled + committed before fire):
  determinism lab — H1 atomics divergence threshold, H2 fp32-vs-fp64 reorder divergence, H3 canon-sort
  digest invariance; controls = serial ordered-reduction reference + fp64 shadow. Converts the QG7
  lane-nondeterminism lesson into a measured operating map. cite fleet-triage PR #1.
- **[open] QO10** (CPU, existing data, ~30m): projection-ladder ablation for the QO1 oracle — feature ladder
  (raw champion state → cv/v/gen → cv only → gen only) × two splits (random stream holdout vs
  later-generation holdout, mirroring their random vs by-ply). Pre-register BOTH directions for the
  shift split: prediction (a) lossier features ≤ raw under random split; (b) lossier features MAY beat raw
  under shift (their L1>L0 inversion). Gates: report random-vs-shift gap per rung; if gen-only ≥ cv under
  shift, the oracle's signal is partly REGIME not STATE — would sharpen QO2 routing (route on regime
  features first).

## PR sweep
fleet-triage #1 (above), #2 resolver triage map (info); canons #4/#5 (scout, referral); pong #88-#92
(C1 scaling lane, Casey's, not ours); nothing open elsewhere touched this wake. [EMBASSY] pong #49 not
re-checked this sweep (day item, unchanged per SCOUT-8/10).

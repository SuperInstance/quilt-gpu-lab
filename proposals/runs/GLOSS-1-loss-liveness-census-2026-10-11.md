# GLOSS-1 — loss-liveness census (pre-registration)

Spawned by SCOUT-98 (slackwater-cognition `score_quality` never reads `game_state`;
degenerate keyword-soup reaches 1.000). Gates frozen from SCOUT-98 wording BEFORE fire.

## Scope (G1 enumeration — the target set)
Scored/loss functions that produce a metric cited by a BOOKED verdict, per
receipts/verdict_index.json (VX-1 index, f516092) + RESULTS.md bookings:

| Module | Function(s) | Booking(s) citing it |
|---|---|---|
| tools/eproc.py | increments, eprocess, kill_gate | QO6, QO6s, PATH-1/THRESH-2 (eproc arm) |
| tools/decision_cell.py | answer_of | QC-JEV, DECIDE-1/1b/1c |
| tools/ensemble_corr_census.py | _pearson, spearman, census | QG7b, D12i |
| experiments/qo10_projection_ladder.py | fit_mlp_seed | QO10 |
| experiments/oracle1.py | logit_fit | QO1 |

Deterministic-run infrastructure (QG7/QG7b training loops, W5b machinery, D12i runner)
is OUT of the in-slice AST scope where it lives outside tools/ — noted, not skipped
silently: their metrics flow through ensemble_corr_census/qcell_sim which ARE in scope.

## Gates (frozen words)
- **G1 (enumeration):** every row above audited; zero silently-skipped scored functions.
- **G2 (unwired-parameter):** param_liveness AST audit over each target function; any
  parameter never read on any path = RED, naming the booking(s) that cite the metric.
  Documented-dead (e.g. `self`, unused CLI plumbing) must be explicitly allowed-listed
  in the receipt or it is a finding.
- **G3 (degenerate-maximum):** construct trivial/degenerate inputs (constant series,
  empty/one-sample, tie-everything) for the pure metrics (eprocess, spearman/_pearson,
  census gates, answer_of argmin law); if a degenerate input reaches the metric's
  optimum while a substantive input scores worse, RED-with-note (Goodhart-shaped
  optimum). Stochastic fit functions (fit_mlp_seed/logit_fit) get the verdict-surface
  treatment via their deterministic heads only (logit_fit is closed-form; probe ties).
- **G4 (attribution):** any RED names the threatened booking explicitly and the slice
  STOPS further queue items until annotated.

## Honest-prior
eproc `witness()` claim=INCREASES arm is already booked dead-but-non-gating (RC-1b,
verdict_index note) — allow-listed, must re-witness as known. QG7b SOFT class
(subprocess nondeterminism) applies to fit_mlp_seed: G2 only, G3 verdict-surface only.

## Cost
CPU only, ~20 min timebox. No GPU. No 429 exposure.

# DECOY-1 — score-vs-own-assignment + clamp-unreachable census (pre-registration)

Spawned by SCOUT-82 (groove-analyzer shape: `genre_coherence` scored against the
already-assigned label — wrongness RAISED the score; plus a `max(0.0, ...)`-clamped
producer whose gate can never fail). Fired from the committed tree; verdict reliance
only after this file is pushed.

## Scope
Every score/metric cited by a BOOKED verdict in RESULTS.md + spool, specifically:
QO1/QO3/QO7-precursor oracle AUC+Brier (tools/auc_sep.py path), DECIDE-1 accuracy /
argmin-consistency / confidence (tools/decision_cell.py:70,75), QG3/QG6/QG7 crossing
rates, DETERM-1 auc_fresh + anchor_in_band, eproc delta evidence (tools/eproc.py),
degrade_gate tolerance check, TIE-1a census verdicts (tools/tie_census.py),
HSA-1b/REPORTER-DEFAULT/DIFFPORT-1/RT-D1 (docs/verification bookings — survey row only).

## Gates (frozen, in words)
- G1 SURVEY: enumerate every booked verdict above with its metric site (file:line or
  docs anchor). A booking citing no computed score is marked N/A-docs.
- G2 CLAMP FLAG: flag any metric site whose value is clamped/floored/ceilinged on the
  side the owning gate tests (clamp-unreachable bound). Positional index clamps
  (bootstrap/CI slicing) are NOT flags.
- G3 SELF-REF FLAG: flag any metric computed against a label/assignment produced by the
  same code path being graded (score-vs-own-assignment).
- G4 MUTATION-LITE on one representative (oracle AUC, QO1/QO3 lineage): shuffled-label
  control must DROP the score below the gate's operating band; a wrong-assignment
  control on any G3-flagged metric must not RAISE it. Failure = RED on the citing booking.

## Verdict rule
RED only when a live cited gate's metric is clamp-unreachable or wrongness-rewarded.
Latent-but-uncited findings (e.g. a clamped confidence never used as a gate) = YELLOW
note, no booking voided.

## Cost
CPU only, ~20 min. No GPU lane.

## Prior
Expected GREEN with possible YELLOW on decision_cell confidence clamps (never cited
as a gate in DECIDE-1..1d bookings — accuracy was the gate).

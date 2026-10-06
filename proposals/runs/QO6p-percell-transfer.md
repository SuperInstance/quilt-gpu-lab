# QO6p — per-cell transfer-legibility audit of QO6/QO6t/QO6n decision-reads (SCOUT-55 spawn)

Spawn: SCOUT-55 2026-10-06 1711Z (rc q9: "validity is PER-CELL, not per-footprint").
Strictly stronger gate than QO6n's dip-depth audit.

## Question
Is every statistic CONSUMED by a QO2 kill/keep decision per-unit-legible (readable from one
stream's own series at decision time) or oracle-sourced — or does any population-aggregate
read feed kill/keep without oracle backing?

## Pre-registered gates (frozen in SCOUT-55, restated)
1. G1 ENUMERATE: decision reads taken from the committed QO6n receipt input list
   (results/qo6n_noise_gap/receipt.json: G1_decision_reads = {retracted, verdict}; consumers
   census = del1_deletion_audit.py, qo6_kill_evidence.py, qo6t_transient_stress.py, qo6n itself).
2. G2 CLASSIFY: each consumed statistic as ORACLE / PER-UNIT / AGGREGATE.
3. G3 VERDICT: RED if any AGGREGATE read feeds kill/keep without an oracle backing; else GREEN.
4. G4 BOOK honestly either way; containment note naming which booked results (if any) the RED
   touches.

## A priori steelman (ST-STEEL convention)
The likely RED is QO6t's rank-series feed (per-gen population CDF rank) — but QO6t is ALREADY
booked MIXED with kill power 0.00 exactly on that feed, so a RED here would CORROBORATE, not
contradict. If instead every feed turns out per-unit or oracle-sourced, QO6n's GREEN upgrades
to the stronger per-cell guarantee and the QO6t failure must be re-read as something else
(power, not legibility) — that would CONTRADICT the SCOUT-55 framing.

## Cost
CPU ~15m. No GPU.

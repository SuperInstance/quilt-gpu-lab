# JV-1 — jev-semantic v0 vs our receipt-manifest doctrine + QO6 evidence layer (2026-10-07 19:2x UTC)

Scope per SCOUT-62 spawn: read jev-semantic v0 (judge_log.py, window.py/window2.py, README,
judges/, play-notes-minimax) + the inbox-014 result; one-page mapping note. Close with no queue
item if nothing maps. Clone read-only at fb1fb29.

## What it is
Append-only judgment log keyed by `(subject, question, judge)` — ALL THREE are git blob hashes,
minted with no central registry. Each judgment is a softmax triple (neg/zero/pos) from a tiny
ONNX student (7 ms ARM, bit-identical cross-arch). window2.py materializes the *latest judgment
per (question, judge)* per subject and tags it: settled +/−/0, CONFLICT (neg>0.3 AND pos>0.3),
ignorance (max < 0.5), lean. Their own play notes: "a judgment is a measurement, not a
derivation: verify by tolerance, not by hash."

## Mapping verdict — it maps, on three rows. CORROBORATE, no new queue item.

1. **Two complementary tiers of evidence.** Our receipt-manifest doctrine covers DETERMINISTIC
   artifacts: hash IS the identity, mismatched bytes refuse to run. Their log covers
   NON-DETERMINISTIC judgments: hash is only the KEY; the value must be verified by tolerance.
   These are the two halves of one doctrine — theirs is the measurement tier our eproc/QO6
   evidence lives in (sigma-honest, retraction-capable), ours is the artifact tier. The 014
   finding ("student smells unreceipted claims as IGNORANCE") is the empirical bridge: an
   unreceipted claim is DISTINGUISHABLE from a received one in judgment space — receipt presence
   is an observable, which strengthens rather than threatens the doctrine.

2. **Disagreement-as-escalation, never averaged.** "a +1 and a −1 averaged to 0 looks like
   'nothing here' when it's conflict" — this is exactly the QG7 ensemble lesson in another
   dialect: single-draw aggregation erases the signal carried by the SPREAD. Their CONFLICT tag
   ~ our retraction-susceptible zone; their "the disagreement IS the escalation signal" ~ our
   booked rule that subpopulation verdicts must be booked as rerun ensembles. No instrument we
   have averages conflicting verdicts; nothing to fix.

3. **Key-shape corroboration of citation discipline.** Keying by blob hash with no registry is
   the same move as RECEIPT-CITE (cite the repo/tree, not the local path) generalized to
   judgments. Independent convergence on hash-addressed identity.

## Instrument-fragility rows (RC-1b class observations, theirs not ours — no action)
- window2.py `tag()` thresholds (0.6/0.3/0.5) are hardcoded, unpinned, untested — the CONFLICT
  band is exactly the kind of gate our FW-1-successor spec says needs a test row.
- `subprocess.run(cmd, shell=True, ...)` in window2 (banned class in OUR tree; noted read-only).
- Judge identity is a string literal ("intuition-student-v1") in judge_log.py while judges/
  manifests exist — the manifest-hash wiring is declared but unwired (their TODO, v0).

## Close-out
Per spawn spec: mapping exists (corroborate rows 1-2) but yields no testable instrument we lack
that isn't already covered by QO6/eproc + receipt doctrine. **No new queue item. JV-1 CLOSED.**

# XP-A2 — instrument-transfer grid at n=6 (entry authored by keeper from banked artifacts; lane died at the summary step after run completed)

- lane: XP-A2 (CPU only; follow-up to XP-A, extends grid 3 -> 6 instruments)
- date: 2026-10-01
- seed: 2718 everywhere; corpus = XP-A's 600 receipts (200 clean / 240 known / 160 held-out), 10 ops
- code: experiments/xp_a2_transfer_grid.py; artifacts: results/xp_a2/{grid.json, run.log, per_receipt_detections.json, judgment_api_receipts.json, c_*.npz, eval_stream.txt}

## Verdict: INCONCLUSIVE at the frozen gates — and the rho gate is now measured, not assumed

- **rho(known, unknown) = 0.493, exact-perm p = 0.32 at n=6** (KEEP needs >= 0.70 AND all-beat-chance; KILL clause: no instrument with known >= 0.65 AND held-out <= 0.50 fired)
- all_beat_chance = **False** (three instruments sit at or below the 0.5/0.6 bars on held-out)
- The n=6 extension did its job: the gate is no longer binary (rho 0.493 is a measured mid-rank, not a rounding artifact of n=3), and it still misses KEEP. The claim "known-power predicts unknown-power" is NOT supported at the grid level — the spread is by DESIGN FAMILY, not by rank.

## Per-instrument table (known recall / held-out recall / clean FPR)

| instrument | family | known | held-out | clean FPR |
|---|---|---|---|---|
| step_parser | invariant-parser | 0.725 | **0.994** | 0.000 |
| digest_manifest | digest-checker | 0.817 | **0.750** | 0.000 |
| g7_field_validator | schema-fields | 0.517 | 0.500 | 0.000 |
| schema_lint | schema-shape | 0.167 | 0.500 | 0.000 |
| verdict_gate_pins | invariant-pin | 0.567 | **0.000** | 0.000 |
| trained_classifier | known-only-learner | 0.408 | 0.287 | 0.225 |
| typesafe JEV (adjunct, n=30 sample) | judgment-API | raw receipts only — see caveat | | |

## Design-family finding (the substantive result, consistent with XP-A)

**Transfer axis = semantic depth, not instrument count.** Two families clear the held-out bar:
- **invariant-parser** (0.994): checks MEANING-bearing invariants (verdict == honest_verdict, tau in grid, wins are strict ints)
- **digest-checker** (0.750): recomputes the receipt binding from cell state — catches ANY drift through the hashed fields

Everything shallow or purely syntactic fails held-out: pins (0.000 — exactly the fleet-triage "given no way to fail" mechanism), schema-shape (0.500 = chance), G7-field-validator ported as pure field checks (0.500 = chance on THESE ops — honest note: those ops corrupt semantic content, not envelope fields; the validator is doing its actual job, which is a different op class), known-only learner (0.287, below chance recall, 22.5% FPR). The judgment-API arm needs a semantics fix before it can be scored (below).

## Typesafe JEV adjunct arm — RAW, not gated (lane died before analysis)

30 sampled receipts through the JEV cell per docs/typesafe-judgment-cells.md (noul graded 0..1). Raw receipts banked in judgment_api_receipts.json. **Caveat booked: the lane's detect convention flags CLEAN receipts (noul 0.45-0.59 on clean -> detect=true in 3 of first 6) — "low confidence" is being read as "detection", which inverts the semantics.** A clean-scored run must gate on corrupted-vs-clean SEPARATION (AUC), not raw detect flags. Follow-up queued (XP-A3): rescore the banked receipts with separation semantics + full-corpus JEV pass.

## Housekeeping

- XP-A2 verdict line in QUEUE.md: INCONCLUSIVE (gates) + design-family finding (real)
- KILL-shape watch: NONE — no instrument with high known-power flunked held-out (digest_manifest, the strongest, transferred at 0.75)
- Lesson: lanes that die at the summary step still bank their data — the keeper folds. Second DeepSeek timeout today (first: XP-A/B z.ai pair); pattern is provider-side, not task-size.

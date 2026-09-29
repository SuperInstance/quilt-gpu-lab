# CM1 round 2 — format-first gate + pinch-threshold sweep (frozen addendum)

Date: 2026-09-29 ~14:1x AKDT. Pushed BEFORE the run. Round-1 plan
(proposals/runs/CM1-cell-mesh-plan.md) governs cells/stimuli/rule/scoring;
this addendum freezes only the deltas.

## Deltas from round 1

1. **Format gate BEFORE semantic gates** (fixes the S7 class): every GEN
   draft is parse-checked first. Unparseable -> one format-feedback retry;
   still unparseable -> PINCH straight to fallback, NO Jev call (tokens
   saved). Parseable -> Jev semantic gates as in round 1.
2. **Pinch-threshold sweep**: arm B runs at p in {0.3, 0.5, 0.7}. Arm A
   unchanged (fresh run, same 12 stimuli, temp 0).

## Path taxonomy (recorded per stimulus per p)

FORMAT_PINCHED / FORMAT_RETRY_PASS / DRAFT_PASS / RETRY_PASS / PINCHED_FALLBACK

## Frozen gates (exact)

Per p: same bands as round 1 (diff vs A: >= +2 GATING_WINS, within 1
TIE_NOISE, <= -2 GATING_HURTS). Secondary (booked, non-gating): Jev input
tokens per stimulus must DROP vs round 1 (9628/12 = 802 avg) — the format
gate's whole point is skipping semantic calls on unparseable drafts.

## Predictions sealed before the run

- S7-class fixed: no unparseable draft reaches Jev.
- S12 wrong at ALL p (fallback router's negation blind-spot is
  threshold-independent).
- At p=0.3 some drafts pass that failed at 0.5 (e.g. S1's urgency gate 0.35);
  direction of accuracy change UNKNOWN — that is the experiment.
- Arm A reproduces 0/12 (deterministic, temp 0).

## Output

results/cm1/round_002_out.json + append results/cm1/rounds.jsonl.
Script: experiments/cm1_relay_r2.py (imports round-1 cells; r1 script stays
byte-frozen for reproducibility).

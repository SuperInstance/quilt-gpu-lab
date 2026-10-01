# CM1-r5 — judge swap + roster under the r4-winning recipe (pre-reg)

Written 2026-09-30 23:2x AKDT, BEFORE fire. One run, no rerolls. Verdict booked in
RESULTS.md regardless of outcome.

## Context (from booked rounds)
- r4: rule-rich batched gates (rule_canon + all reports in judge state, ONE batched
  typesafe call, 24 noul questions) = **12/12, 25× faster judge wall, 4.5× cheaper**
  than rule-blind per-stimulus gates. Verdict RICH_WINS; root cause: r3's gates
  judged without the RULE and fabricated doubt.
- r3/r4 corpus saturated at 12/12 → raw accuracy can no longer discriminate.
  **r5 gates on transfer + roster-rescue + calibration, not accuracy.**

## Factors (declared, both fresh this round)
1. **Judge swap**: jev-preview → **jev-latest** (r4's tsafe_batch used jev-preview).
2. **Roster**: single GEN cell vs 3-cell roster (DeepInfra, temperature 0):
   - `ByteDance/Seed-2.0-mini` (r3/r4 incumbent)
   - `XiaomiMiMo/MiMo-V2.6-Flash`
   - `inclusionAI/Ling-3.0-flash`

## Arms
- **Arm A (TRANSFER)** — r4's exact winning recipe, one factor changed: single GEN
  (Seed-2.0-mini), 12 ungated drafts (+ FORMAT_FEEDBACK retry), ONE rule-rich batched
  judge (24 noul questions, jev-latest), PINCH=0.5, doubted→feedback retry→2nd batch,
  pinched→`keyword_router`. Question: does the recipe transfer under jev-latest?
- **Arm B (ROSTER)** — 3 cells × 12 stimuli = 36 ungated drafts (+ FORMAT_FEEDBACK
  retry per draft), ONE rule-rich batched judge over ALL drafts (72 noul questions,
  keys `<ci>_<sid>_{domain,urgency}_ok`, jev-latest), then per stimulus:
  served draft = **argmax min(gd,gu) among gate-passing drafts** (both ≥ 0.5;
  deterministic tiebreak: lower cell index). No gate-passing draft → `keyword_router`
  pinch. No parseable draft at all → FORMAT_PINCHED path.

## Frozen gates
- **H1 (roster recipe works)**: B ≥ 11/12 → KEEP; B ≤ 8 → KILL; else WEAK_UNRESOLVED.
- **H2 (recipe transfers under jev-latest)**: A ≥ 11/12 → TRANSFERS; A ≤ 8 →
  TRANSFER_FAILS; else WEAK.
- **H3 (honest conditional)**:
  - B > A → ROSTER_EARNS (book rescued sids: ones A missed that B serves correctly).
  - B == A == 12 → ROSTER_IDLE (saturation: no rescue opportunity existed — this is
    the EXPECTED outcome given r3/r4; booking it is not a failure).
  - B < A → ROSTER_HURTS.
- **Calibration** (informational): mean noul of passing gates on correct svserved
  drafts, per arm; A vs r4's B-cal under jev-preview is the judge-swap read.
- **Cost bars (frozen)**: A = 24 jev questions (r4-B parity); B = 72 (3× A);
  bar: B jev tokens ≤ 3.5× A. DI tokens: B ≈ 3× A (36 vs 12 drafts).

## Harness gates (pre-run)
- Cell smoke before arms: 1-token ping per cell, 2 attempts. A cell that fails both
  → booked DEAD, roster continues with survivors. <2 survivors → HARNESS_INVALID,
  abort WITHOUT scoring (no silent substitution of the roster).
- PARSE_FAIL after retry → format-pinched path, counted in B_paths (never dropped).
- Batched judge missing any answer key → retry once → still missing → HARNESS_INVALID.
- Output: results/cm1/round_005_out.json (schema cm1-round5/1) + rounds.jsonl append.

## Rules
One run. No rerolls on ugly numbers — ugly numbers are results. Confounds booked in
the receipt (model version drift on hosted endpoints, jev-latest behavior deltas).

# DECIDE-1d — instruction-ablation census (pre-registration)

**Spawned by:** DECIDE-1c (instruction-BLIND, not sign-flipped). **Status at write:** PRE-REGISTERED, not fired.

## Question
Does ANY instruction phrasing move jeff-0.8b's prediction off the argmin-balance candidate, or is the argmin lock absolute in the backbone representation?

## Design
Identical lane to DECIDE-1b/1c (same 64 questions, seed 202, zeroshot reader, no re-sampling). Only the instruction string varies. Variants:

1. `largest` (baseline; already booked: argmax 5/64, argmin 0.891 — reuse, do not re-run)
2. `smallest` (DECIDE-1c; reuse)
3. `highest balance` (synonym swap of largest)
4. `lowest balance` (synonym swap of smallest)
5. neutral: "Choose one edit." (no criterion)
6. superlative-only, definition dropped: "Which single edit gives the largest balance?"

## Gates (pre-declared)
- **D1 (lock-break):** PASS if ANY variant's pred_is_argmin_balance drops below 0.75 (i.e., some phrasing unlocks the representation). Which variant + how far is the deliverable.
- **D2 (argmax recovery):** PASS if any variant's argmax-balance accuracy clears 0.75 — the cell answers the asked question.
- **D3 (neutral fallback):** with no criterion, report argmin-share and kind census. Prediction: still argmin-locked (the lock is representation-driven, not instruction-driven).
- Exploratory: per-variant pred-kind census (delete/insert/replace shares).

## Predictions (falsifiable)
- P1: no variant moves argmin consistency below 0.75 (lock absolute) — expected given 1b/1c.
- P2: neutral instruction unchanged behavior vs `largest`.
- P3: dropping the definition sentence changes nothing (the model never used it on this lane).

## STOP rule
If all variants hold argmin >= 0.75, name the lock ("representation-locked argmin"), close DECIDE-1 lane for tonight, no further instruction work. No re-rolls on any single variant.

## Budget
4 variants x 64 questions ~ 256 decides, ~1.7 GiB VRAM class, ~8 min.

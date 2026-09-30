# DECIDE-1c — confirmatory instruction flip (2026-09-30 02:2x, pre-registered BEFORE firing)

## Question
DECIDE-1b showed jeff-0.8b answers "which edit gives the SMALLEST balance" on the lane (argmin-balance
consistency 0.891) while the instructions ask for the LARGEST. Hypothesis: signed-superlative flip — the
backbone tracks balance faithfully but flips the superlative direction. DECIDE-1c flips the instruction word
"largest" -> "smallest" and predicts the choice flips with it.

## Lane (frozen)
Identical to DECIDE-1b except instructions string: "...Which single edit gives the smallest balance?"
Same 64 questions (make_questions(64, seed=202)), zeroshot reader, no re-sampling, labels unchanged
(label = argmax-balance, the true best edit).

## Predictions (frozen, falsifiable)
- **C1 FLIP-CONFIRMED**: pred_is_argmax_balance >= 0.75 (mirror of 1b's 0.891 argmin consistency).
- **C2 accuracy MIRROR**: argmax accuracy jumps to >= 0.75 (since label = argmax-balance; if the model
  now picks argmax, it is accidentally CORRECT). CP95 computed.
- **C3 shuffled-reader symmetry**: content_following stays >= 0.7 (still reads content, not letters).
- **STOP rule**: if C1 fails (consistency near 0.5 or still argmin), the signed-flip hypothesis is dead —
  book as REFUTED, do not re-roll; spawn new diagnosis item.

## Gates
C1 and C2 as above at 95% (Wilson). Exploratory: kind census (expect insert-preferring now, mirror of 1b).

## Hardware
Peak VRAM bar 6 GiB; expect ~1.7 GiB (1b run).

Artifacts: experiments/decide1c.py, results/decide1/decide1c_results.json.

## Pinned instruments

Retroactively sealed 2026-09-30 (RECEIPT-HASH): instrument hashes for the tools
used by this run are pinned in `receipts/tool_pins_2026-09-30.md` (snapshot as of
seal time, not fire time — earliest verifiable baseline). Forward-looking receipts
pin at fire time.

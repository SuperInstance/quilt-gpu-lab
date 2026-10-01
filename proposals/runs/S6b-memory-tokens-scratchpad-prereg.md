# S6b — does the loop need somewhere to write? (edge-mine M16 falsifier on our own physics)

owner: farm
Seeded by: edge-mine Wave 7 (M16 — looped depth seems to need a scratchpad; memory tokens required).
GPU, ≤3 GPU-hr/arm, 3 arms. Runner (to write): `experiments/s6b_memory_tokens.py` — elephant-gpu venv,
bf16, preflight VRAM guard. Receipt: `results/s6b_memory_tokens.json`.

## Question (one)
The D12j law says T_floor ~ C(N,p)/W for evidence-integrating discovery. Does giving the loop a
scratchpad change C (real evidence-efficiency gain), or does any "win" just track capacity?

## Design (frozen)
- Tiny looped transformer (~8–12M params, bf16): transformer block applied R times per discovery round.
- Arms: **MEM** — 4 persistent memory tokens, read/written every loop iteration; **NOMEM** — same loop,
  no persistent tokens; **MATCH** — param-matched control (extra width, no scratchpad).
- Task: the D-line discovery game itself — model consumes T rounds of correlated-pair stream tokens,
  predicts partner IDs (first-index tie-break, argmax rule as in D12i/D12j).
- Eval corners (frozen): (W,N,p) ∈ {(32,128,0.3), (64,128,0.3), (64,64,0.5)}, T ladder 1..32, 5 draws
  each, acc bar 0.9, floor = min T reaching the bar (same convention as D12i/D12j).
- Training: mid-ladder corners only; floors read on the frozen corners. Budget bust → DOWN-SCALE the
  model and declare it; never widen a tolerance.

## Gates (frozen, mechanical)
- **WRITE_HELPS**: T_floor(MEM) < T_floor(NOMEM) at ≥2/3 corners AND T_floor(MEM) ≤ T_floor(MATCH)
  at ≥2/3 corners → the scratchpad changes C. Feeds the looped-substrate design directly.
- **WRITE_NEUTRAL**: |Δ| ≤ 1 ladder rung everywhere → M16 does not transfer to our physics; booked
  negative, S6b closes.
- **CAPACITY_CONFOUND**: MEM beats NOMEM but MATCH matches MEM → the win is size, not a scratchpad.
  Book as confound; do not spin.
No post-hoc corners, no bar moves. One question per pre-reg.

## Pre-fire amendment (2026-10-01, committed BEFORE any measured run — two-witness review: kimi+zcode)
- Scalar-token design pinned: each e_t[j] is one token (Linear(1→d)); self channel stays pinned 0 (d12j convention, verified). Readout pools per-channel token outputs over (T,N); MEM concatenates mean mem state (read_d=2d as declared). Mem-token state split at N_MEM (first 4 slots = memory, remainder = channel tokens).
- KILL-harness receipts go to attempt-stamped filenames — never overwrite a non-KILL receipt.
- If any arm in a gate comparison is budget-capped (3h wall), the verdict reads INCONCLUSIVE-CAPPED (booked as such — not a gate verdict).
- Eval precision: fp32 (measurement choice, declared); training bf16 per frozen recipe. Bar 0.9 over 5 draws = 5/5 (declared).
- Receipt carries per-arm wall_s + the eval seed rule.

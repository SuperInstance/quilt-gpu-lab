# XQ0 — does consolidation-by-substrate think? (G0 falsifier)

owner: farm
Program: docs/XQ-PROGRAM.md (G0). GPU, ≤3 GPU-hr/arm, 4 arms.
Runner: experiments/xq0_substrate_consolidation.py (written-untested; owning lane
reviews before fire; fail-loud KILL-harness receipts).

## Question (one)
An NN that externalizes state into a quilt (learned annotation writes) and reads back
CONSOLIDATED state (F>0 flow steps between timesteps) — does it integrate evidence
better than the same NN with (a) no external memory and (b) passive external memory
(F=0, state persists but nothing consolidates)? The physics, not the extra space, is
the claim under test.

## Design (frozen)
- Task: partner-of-channel-0 discovery, d12j-exact streams (same generator as S6b,
  verbatim copy). Evidence vector e_t (N-dim) per timestep.
- Quilt: q=16 grid (256 cells). LAYOUT (frozen): cells [0..N) = evidence block,
  harness-SET to 3·e_t each timestep (±3 scale = the oracle's inject convention);
  cells [N..q²) = annotation block, SET each timestep by the NN's write head
  (3·tanh). After both writes: F flow steps (k=0.22, res=0.4 — oracle semantics,
  torch re-implementation, gradients flow through: the dynamics are differentiable).
  Quilt arms read the FULL field every timestep (token = [e_t ; field]).
- Arms: **NOMEM** (d=1024, no quilt, mean-pool readout — S6b NOMEM twin),
  **MATCH** (d=1088, no quilt, extra width), **PASSIVE** (d=1024, quilt F=0,
  final-token readout), **QFLOW** (d=1024, quilt F=4, final-token readout).
  Declared asymmetry: quilt arms read final state (integration lives outside);
  no-quilt arms pool (integration lives inside). That IS the comparison.
- Training: S6b recipe verbatim — corners {(8,32,0.3),(16,64,0.3),(16,32,0.5),
  (32,64,0.7)}, T~U{1..16}, 30k steps, batch 64, bf16, AdamW 3e-4, ≤3h wall/arm.
- Eval: frozen corners {(32,128,0.3),(64,128,0.3),(64,64,0.5)}, T ladder 1..32,
  5 draws, acc bar 0.9, floor = min T at bar.

## Gates (frozen, mechanical — priority top-down)
- **SUBSTRATE_THINKS**: QFLOW floor < PASSIVE floor at ≥2/3 corners. The consolidation
  does work beyond storage. (Program thesis live.)
- **EXTERNAL_HELPS**: min(PASSIVE,QFLOW) floor < NOMEM floor at ≥2/3 corners AND
  ≤ MATCH at ≥2/3. External state helps; maybe only as storage.
- **CAPACITY_CONFOUND**: MATCH ≤ every quilt arm everywhere → book, don't spin.
- **DEAD_SUBSTRATE / MIXED** otherwise → G0 closes, next axis from the ledger.
Cross-check: NOMEM here must reproduce S6b's NOMEM floors (same seeds/code) — a
mismatch is booked as variance evidence before any gate is read.
Kill-clause: no tolerance loosening, no re-rolls, no post-hoc corners.

## Pre-fire amendment (2026-10-01, committed BEFORE any measured run — two-witness review: kimi+zcode)
- Varying-N pinned: quilt layout follows the batch's actual N — cells [0..N) evidence / [N..q²) annotation; model input pads ev channels with zeros to n_channels (missing channels carry no evidence; partner ids < N always). Fixes the step-0 crash at train corners N∈{32,64}.
- KILL-harness receipts go to attempt-stamped filenames — never overwrite a non-KILL receipt.
- If any arm in a gate comparison is budget-capped (3h wall), the verdict reads INCONCLUSIVE-CAPPED (booked as such — not a gate verdict).
- Eval precision: fp32 (measurement choice, declared). Training stays bf16 per frozen recipe.
- Verified-correct under review (booked, no change): S/N/E/W pad directions + border sentinels; the DEAD_SUBSTRATE / MIXED fail token matches this prereg as written.

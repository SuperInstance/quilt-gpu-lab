# CX-CHEAP-0 — per-item win prediction + MLP retirement test (CPU, ~2.2 s, 0 Wh)

- lane: CX-CHEAP-0 (follow-through of RING-CX-2 trilogy closure) · device: **CPU only, numpy+sklearn**
  (no GPU, no torch) · seed 2718 · **~2.2 s wall, 0 Wh** · reuses `experiments/ring_cx2.py` harness
  wholesale (COMP1 word-view featurization, answer margins, disagreement features, frozen 0-param
  centroid-Pearson router, split discipline).
- wiring: router held-out top-1 **0.7356 == booked 0.7356** (EXACT, wiring check green). Split 1810 / 590.
- honest note: COMP1's saved artifacts do **not** persist per-item per-arm predictions (only aggregate
  boards/CIs), so per-item FED/SINGLE correctness is **re-derived** from the same frozen COMP1
  featurization + router + split (ring_cx2 recipe), not read from a file.

## Q1 — can a cheap gate predict the PER-ITEM FED−SINGLE win?
label = 1[FED correct AND SINGLE wrong]; held-out base rate **0.1746** (103 wins / 590; 81 losses = FED
wrong & SINGLE right).

| feature set | feats | held-out AUC | Brier | prec/base @Youden | boot std (5) | gate |
|---|---|---|---|---|---|---|
| f_margins {4 margins} | 4 | 0.5949 | 0.1422 | 1.191 | 0.0101 | **FAIL** |
| f_disagree {d_ans,d_conf} | 2 | **0.9223** | 0.0777 | 3.207 | **0.0000** | **INCONCLUSIVE** (frost law) |
| f_both {margins+disagree} | 6 | 0.9189 | 0.0780 | 3.207 | 0.0070 | **PASS** |
| f_oracle {+per-sensor correct (leaky)} | 10 | 0.9432 | 0.0729 | 3.207 | 0.0044 | PASS (ORACLE, non-deployable) |
| +per-sensor disagreement (deployable) | 10 | 0.9276 | 0.0764 | 3.207 | 0.0070 | PASS |

- single-feature AUC: d_ans **0.9168** · d_conf 0.4813 · margins (mean/max) 0.4838/0.4812 ·
  0-param router-is-blind control 0.5628. **The carrier is the 2-arm disagreement, not the margins.**
- **G-C1 PASS** (best deployable f_both 0.9189 ≥ 0.70, and f_disagree 0.9223). **G-C2 PASS**
  (prec/base 3.207 ≥ 2×, Youden precision 0.56 vs base 0.175). **G-C3** — f_both std 0.00701 > 0 PASS;
  **f_disagree std 0.0000 → INCONCLUSIVE, never PASS** (exact-degenerate binary feature, frost law).
- **SEPARATION DECOMPOSITION (the honest headline):** `win ⟹ FED≠SINGLE` is a **necessary condition**
  (0/103 wins agree). win-rate | disagree = **0.5598** (3.2× base); win-rate | agree = **0.0**. But
  *within* the disagreement set **no feature separates win from loss** — within-disagreement AUC:
  margins 0.473/0.483, d_conf 0.533, FED-confidence 0.539, SINGLE-confidence 0.467 (≈ chance). So the
  AUC ≈ 0.92 is the **necessary-condition boundary**, not a learned per-item predictor. The cheap
  margins (the RING-CX-2 winner) are **near-chance here (0.595)**; adding an inert feature (d_conf) is
  what de-degenerates the bootstrap and flips f_disagree from INCONCLUSIVE to f_both PASS.

## Q2 — does the cheap 325-param two-arm retire COMP1's 4228-param FED MLP?
cheap two-arm = SINGLE logistic (65p) + 4 per-regime logistic cells (4×65p) + frozen 0-param router =
**325 params, CPU, 0 Wh** vs COMP1 FED **4228 params, GPU, 11.76 Wh** (13.0×).

| regime | COMP1 FED (4228p, booked seed-mean) | cheap FED (325p) | Δ |
|---|---|---|---|
| full | 0.5605 | 0.5814 | **+0.0209** |
| semantic | 0.5816 | 0.5957 | +0.0141 |
| counting-address | 0.5731 | 0.5612 | −0.0119 |
| negation-scope | 0.5541 | 0.6081 | **+0.0540** |
| agent-role | 0.5370 | 0.5617 | +0.0247 |

- negation win: cheap **+0.1959** vs COMP1 **+0.1262** → ≥ gate threshold ✅.
- **gate = per-regime |Δ| ≤ 0.02 everywhere AND negation win ≥ +0.126 → FAIL** (max |Δ| = 0.054 at
  negation; full +0.021). Full Δ = +0.0209 ≈ **3.7× COMP1's seed-std (0.0056)** — real, not noise.
- **verdict as pre-registered: FAIL — the MLP buys "something."** Nuance the gate cannot encode: the
  failure direction is **cheap-better** — the 325p two-arm ≥ COMP1 FED on 4/5 regimes (only
  counting-address is lower, −0.012). So the MLP does not buy accuracy on this corpus; it buys
  **regime-symmetry** (a flat, drop-in profile) — the cheap arm *redistributes* accuracy toward negation.

## economics
- 325 params · CPU · **0 Wh** · 2.2 s  vs  4228 params · GPU (cuda) · **11.76 Wh**. 13.0× params, ∞×
  energy for a model that is *not* a drop-in replacement (but is ≥ it where it matters).

## verdict / answers
- **Q1:** a cheap **deployable** gate *does* clear AUC ≥ 0.70 (f_both 0.9189, prec/base 3.21, std>0) —
  but the signal is **structural**: FED≠SINGLE is a necessary condition for the win and the disagreement
  set is 3.2× enriched (0.56 vs 0.175); **no feature predicts *which* disagreements are wins**
  (within-set AUC ≈ 0.53). Book: *per-item win is not predictable beyond its necessary condition.*
- **Q2:** as pre-registered, **FAIL — MLP not retired** (per-regime |Δ| ≤ 0.02 broken by negation
  +0.054). Substantively the 325p CPU two-arm matches/beats the 4228p GPU MLP on 4/5 regimes incl. the
  decisive negation win (+0.196 vs +0.126), so the MLP's 13× params buy regime-flatness, not value.

## artifacts
- code `experiments/cx_cheap0.py` · results `results/cx_cheap0/cx_cheap0_results.json`
- reuse lineage: `experiments/ring_cx2.py`, `experiments/ring_cx0.py` (feat_word/pearson/REGIMES),
  `results/comp1/comp1_results.json` (booked 4228p FED boards + router 0.7356).
- **NOT COMMITTED.**

## next question
Within the disagreement set, is *anything* learnable (per-regime calibration of the FED−SINGLE
disagreement; the win_rate|disagree is 0.56 overall — is it regime-modulated?), or is the win
fundamentally a coin-flip once the arms disagree? And: can a **regime-conditioned** cheap gate recover
COMP1's FED regime-flatness (counting-address −0.012) without the 4228p MLP?

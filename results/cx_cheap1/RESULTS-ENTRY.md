# CX-CHEAP-1 — within-disagreement learnability + regime-conditioned cheap gate (CPU, ~3.1 s, 0 Wh)

- lane: CX-CHEAP-1 (closing move of the cheap-gate thread; spawned by CX-CHEAP-0) · device: **CPU only,
  numpy+sklearn** (no GPU, no torch) · seed 2718 · **~3.1 s wall, 0 Wh** · reuses `experiments/cx_cheap0.py`
  wholesale (`fit_gate`/`answer_margins`/`youden`/2-arm recipe) + `experiments/ring_cx0.py`
  (`feat_word`/`pearson`/`REGIMES`).
- wiring: router held-out top-1 **0.735593 → 0.7356 == booked 0.7356** (match at 4 dp, wiring check green).
  Split 1810 / 590.

## Q1′ — is ANYTHING learnable WITHIN the disagreement set?
Restrict to held-out **FED ≠ SINGLE** items: **n = 184**, of which **103 are wins**
(win = FED correct AND SINGLE wrong). win-rate | disagree = **0.5598** (3.2× the full base 0.1746).
Inner-set label = win vs loss. Models fit on TRAIN-disagreement, evaluated on HELD-OUT-disagreement.

| feature set (deployable) | k | logistic AUC | tree(d2) AUC | best | G-D1 (≥0.60) |
|---|---|---|---|---|---|
| regime one-hots (**router-picked**) | 4 | 0.5003 | 0.4975 | 0.5003 | FAIL |
| confidences {d_conf, FED-conf, SINGLE-conf} | 3 | 0.5370 | 0.5454 | 0.5454 | FAIL |
| margins {4 answer margins} | 4 | 0.4345 | 0.5120 | 0.5120 | FAIL |
| d_ans (constant ≡ 1 inside the set) | 1 | 0.5000 | 0.5000 | 0.5000 | FAIL |
| **ALL deployable** (oh+conf+margins+d_ans) | 12 | 0.5337 | 0.5448 | **0.5448** | FAIL |
| ALL without the degenerate d_ans | 11 | 0.5337 | 0.5448 | **0.5448** | FAIL |

- bootstrap within-set AUC std (5 refits): ALL 0.0346 · regime-oh 0.0244 · confidences 0.0097 — **all > 0**
  (not a frost-law degeneracy; the near-chance result is real, not an artefact of a constant predictor).
- **d_ans is degenerate inside the set (≡ 1):** confirms CX-CHEAP-0's decomposition — the whole outer AUC
  (0.92) is the *necessary condition* boundary `win ⟹ FED≠SINGLE`, and it carries **zero** within-set info.
- **regime win-rate | disagree (the descriptive structure):**

| true regime | n_disagree | n_win | win-rate \| disagree |
|---|---|---|---|
| semantic | 40 | 16 | **0.400** |
| counting-address | 38 | 19 | **0.500** |
| **negation-scope** | 57 | 43 | **0.754** |
| agent-role | 49 | 25 | **0.510** |

- **Oracle twist (honest):** the *true*-regime one-hot **does** carry within-set signal —
  negation-scope one-hot AUC **0.6223**, and a true-regime 4-way logistic **0.6173** (train→held-out) ≥ 0.60.
  But it is **non-deployable**: the only regime signal available at inference is the frozen 0-param router,
  whose pick is **chance inside the disagreement set (AUC 0.5003)**. The win-rate *is* regime-modulated
  (negation 0.75 vs 0.40–0.51) — the router just cannot resolve regime where it matters.
- **G-D1 → FAIL for every deployable feature set** (best 0.5448 < 0.60). **Book: per-item win is chance
  within the disagreement set for any deployable feature; cheap gates localize the boundary, never the wins.**
  (Regime structure exists only in the oracle true-regime label, which the deployable router cannot deliver.)

## Q2′ — can a REGIME-CONDITIONED cheap gate retire COMP1's 4228p FED MLP?
Reference = CX-CHEAP-0's 325p two-arm (SINGLE 65p + 4 per-regime 65p cells, router-selected).
COMP1 booked 4228p GPU FED: full 0.5605 · semantic 0.5816 · counting-address 0.5731 · negation-scope 0.5541 ·
agent-role 0.5370. Δ = cheap − COMP1.

| variant | params | full | semantic | counting-addr | negation | agent-role | max\|Δ\| | worst Δ | neg win | G-E2 |
|---|---|---|---|---|---|---|---|---|---|---|
| **v1 cells** (CX-CHEAP-0) | 325 | +0.0209 | +0.0141 | **−0.0119** | **+0.0540** | +0.0247 | 0.0540 | −0.0119 | **+0.1959** | ✅ |
| **v4 cells + per-regime intercept** | 329 | +0.0090 | +0.0141 | −0.0263 | +0.0135 | +0.0309 | 0.0309 | −0.0263 | +0.1554 | ✅ |
| **v2 regime-conditioned pooled** [word64+4 router oh] | **69** | −0.0164 | +0.0638 | **−0.0048** | **−0.1487** | +0.0247 | 0.1487 | −0.1487 | **−0.0068** | ❌ |
| v2 + per-regime intercept | 73 | −0.0097 | +0.0567 | −0.0263 | −0.1217 | +0.0494 | 0.1217 | −0.1217 | +0.0203 | ❌ |
| v2 on **TRUE**-regime one-hots (ORACLE) | 69 | +0.0005 | +0.0567 | −0.0119 | −0.1149 | +0.0679 | 0.1149 | −0.1149 | +0.0270 | ❌ |

- **G-E3 (boot std > 0, 5 refits): PASS for all** — v1 0.0140, v4 0.0200, v2 0.0216, v2+int 0.0116.
- **G-E1 literal two-sided |Δ| ≤ 0.02 → FAIL for every variant.** Only v1/v4 satisfy the **one-sided
  drop-in reading** (cheap not materially worse, worst Δ ≥ −0.02): v1 worst Δ −0.0119 ✅.
- **The regime-conditioning trade is strict and is the finding.** Adding 4 router-regime one-hots to a
  pooled logistic (v2, 69p) **DOES recover the counting-address flatness** — Δ −0.0119 → **−0.0048** — the
  exact stated goal — but it **destroys the negation win** (+0.196 → **−0.007**, G-E2 ❌). The 4-way oracle
  variant shows this is not a routing error: even with *true* regime one-hots, negation collapses to −0.115.
  Flatness and the negation win come from the **same specialist structure** — you cannot buy one back with a
  pooled regime-conditioned readout without paying the other.
- **Verdict as pre-registered: FAIL — MLP not retired** (G-E1 two-sided broken). The MLP's unmatchable value
  is now precisely named: **it holds regime-flatness AND the +0.126 negation win simultaneously**; every cheap
  variant, incl. the regime-conditioned ones, buys one at the cost of the other. Under the weaker one-sided
  drop-in reading the unchanged **325p v1 already PASSES** — the MLP buys *symmetry*, not accuracy.

## economics
- 69–329 params · CPU · **0 Wh** · 3.1 s vs 4228 params · GPU (cuda) · **11.76 Wh** (57.9× at 73p, 61.3× at 69p).

## artifacts
- code `experiments/cx_cheap1.py` · results `results/cx_cheap1/cx_cheap1_results.json`
- lineage: `experiments/cx_cheap0.py` → `ring_cx2.py` → `ring_cx0.py`; `results/comp1/comp1_results.json`
  (booked 4228p FED boards + router 0.7356). **NOT COMMITTED.**

## next question
If the negation win and regime-flatness are the same specialist structure, the cheap gate cannot be a *diff*
of the MLP — it can only be *better where it is better*. So: is the COMP1 *board* (per-regime accuracy) even
the right target, or should a cheap federation be judged on the **negation win alone** (where federation has
demonstrated value) with flatness dropped as a gate? And: can a **router-repair** (the frozen 0-param router
is chance inside the disagreement set) recover the oracle's true-regime signal (0.617) at 0 params?

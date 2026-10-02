# RING-CX-2 — SYNTH-0 wildcard trilogy, FINAL probe: the CHEAP TRAINED gate

**Lane:** RING-CX-2 · **Date:** 2026-10-01 16:4x AKDT · **Seed:** 2718
**Device:** CPU only (numpy + sklearn) · **GPU:** not used · **torch:** not used · **0 Wh**
**Commit:** none (lane does not commit) · **Wall:** ~2.3 s
**Reuses:** `experiments/ring_cx0.py` (featurization + 0-param router) and the ring_cx1
answer-margin doctrine.

---

## The question (booked by RING-CX-1)

RING-CX-0/1 closed the wildcard thread **negative**: no *untrained* gate sees the blind
regime (certainty Reject 0.127; margin gate ratio 0.789 = chance routing), and the ring's
relu-homogeneous update makes any margin gate through it *provably* a **shape** gate
(scale-invariant in the cue vector). **Open question: is the blindness reachable by a
CHEAP TRAINED gate — does cheapness live in the GATE, not the geometry?**

## (1) Wiring bill of health

Rebuilt the frozen COMP1 word-view featurization (sha1 BoW D=64, L2) + the frozen
0-parameter regime-centroid Pearson router on TRAIN only. Held-out top-1 = **0.7356**,
bit-equal to COMP1's booked `router_audit.heldout_acc` **0.7356**. Same TRAIN/held-out
split as ring_cx0/1 (`sha256[0] < 'c'`): 1810 train / 590 held-out; negation 148 (25.1 %).

## (2) The CHEAP two-arm build (all CPU, sklearn, TRAIN-only, seed 2718)

COMP1's per-item arm predictions were never persisted, so the FED−SINGLE disagreement was
rebuilt **from scratch with cheap linear arms** (this is itself the point — 325 params, no GPU):

- **SINGLE arm** — one binary logistic on the 64-dim word view → `P(canon)`. 65 params.
- **FED arm** — 4 per-regime logistic cells (each fit on that regime's TRAIN items),
  selected per item by the **same frozen 0-param centroid-Pearson router**; FED read =
  selected cell's `P(canon)`. 260 params. **Whole bank = 325 params** vs COMP1's trained
  FED arm **4228 params / GPU / 11.76 Wh**.

**Per-item disagreement** (gate feature (b)): primary `d_ans = 1[FED ans ≠ SINGLE ans]`;
sensitivities `d_conf = p_fed − p_single`, `d_corr = 1[FED correct] − 1[SINGLE correct]`.

**The cheap arms reproduce COMP1's negation win** (held-out acc):

| arm | overall | semantic | counting | **negation** | agent-role |
|---|---|---|---|---|---|
| SINGLE (65p) | 0.5441 | 0.6525 | 0.5612 | **0.4122** | 0.5556 |
| FED (260p + router) | 0.5814 | 0.5957 | 0.5612 | **0.6081** | 0.5617 |

FED − SINGLE @ negation = **+0.196** (COMP1's trained nets: +0.126). Federation value is
**reproducible by cheap linear cells** at 1/13 of the FED arm's parameters and 0 GPU.

## (3) GATES (pre-registered, seed 2718)

Gate target = **blindness alert** (1 iff held item's regime is the blind regime,
`negation-scope`). Alert = `p ≥ 0.5`. `StandardScaler → LogisticRegression`, TRAIN-only.

| gate | feature set | params | G-T1 negation rate ≥2× mean | G-T2 precision ≥0.5 | G-T3 degr ≤0.10 | G-T4 boot std>0 | verdict |
|---|---|---|---|---|---|---|---|
| **(a)** | **4 per-sensor margins** | **5** | neg **0.6689** vs mean 0.2055 → **3.255** ✅ | **0.805** ✅ | 0.041 (AUC 0.920→0.878) ✅ | **0.0131** ✅ | **PASS** |
| (b) | disagreement `d_ans` (1 feat) | 2 | degenerate: 0 alerts → ratio n/a ❌ | n/a ❌ | −0.019 | **0.0000** ❌ | **INCONCLUSIVE** |
| (c) | margins + disagreement (5 feat) | 6 | neg 0.6554 vs 0.1988 → **3.297** ✅ | **0.815** ✅ | 0.042 (0.920→0.877) ✅ | 0.0184 ✅ | **PASS** |

- **(a) PASSES ALONE — at 5 parameters.** Alert concentrates hard on the blind regime:
  semantic 0.007, counting 0.029, **negation 0.669**, agent-role 0.117.
- **(b) carries no usable signal.** `d_ans` is ~uniform across regimes (0.27–0.39) and has
  held-out AUC **0.549**. A 0.5 threshold yields **0 alerts** → the frost law fires
  (std = 0) → **INCONCLUSIVE, never PASS**. Sensitivities: `d_conf` AUC 0.539, `d_corr`
  AUC 0.590; under a **prevalence-matched TRAIN-quantile threshold** (house τ doctrine)
  `d_ans` alerts 31 % overall but only 38.5 % on negation → ratio **1.238**, precision
  **0.310** (fails T1/T2). The cheap per-item disagreement is **not** the carrier.
- **(c) = (a).** Adding the disagreement changes nothing (ratio 3.297 vs 3.255; the extra
  feature is inert). Margins are not riders — the disagreement is.

**Which feature set carries the signal: the 4 per-sensor MARGINS, alone.** Cheap
answer-geometry, once a *linear trained* readout is applied, reaches the blind regime.

### Control: is the gate more than the router's argmax? (0-param baseline)

"Alert iff the router's top sensor == negation sensor" (0 params) already gives neg
**0.703** vs mean 0.280 → ratio **2.508**, precision **0.619**. The 5-param margin gate
(3.255 / 0.805) beats it, but the signal it reads is the same **regime identifiability**
already present in the corpus geometry — a *linear trained* readout recovers what the
untrained ring's scale-invariant Reject could not.

### Feature correlation with the blindness label (held-out)

`max-margin +0.229`, `mean-margin +0.205`, `d_corr +0.165`, `d_ans +0.092`. The margins
carry the most, and they carry exactly the regime axis.

## Verdict

**PASS (2/3 feature sets).** **Cheapness DOES live in the gate.** A **5-parameter**
trained logistic on the *untrained* 4-margin geometry reaches the blind regime at
negation alert-rate **0.669 = 3.26×** the regime mean, precision **0.805**, with
train→held-out AUC degradation of only **0.041** and bootstrap std **0.0131**. The
trilogy's negative is thereby *resolved*: untrained gates fail because a relu ring is a
shape gate that destroys the level information; a trained linear readout reads the levels
and the regime geometry is trivially recoverable.

**But the caveat is sharp and pre-registered-visible:** the gate detects the **regime**
(≈ the 0-param router-argmax baseline, ratio 2.5), **not** the FED−SINGLE *disagreement*
signal — as a cheap standalone per-item feature that disagreement is **dead** (AUC 0.55;
0 alerts at threshold; ratio 1.24 prevalence-matched). Reaching the blind *regime* ≠
detecting the per-item *answer win*.

## The one-line closure of the trilogy

**Untrained geometry is blind, but 5 trained parameters read it and reach the blind
regime — cheapness lives in the gate; yet the carriers are the margins (regime
geometry), not the cheap FED−SINGLE disagreement, which carries nothing at per-item
resolution.**

## Next question

The cheap gate identifies the **regime** (and only that), so it duplicates the 0-param
router rather than predicting the **per-item FED win**. The wiring gate COMPOSITE-2
actually needs is one that predicts, per item, *whether FED will beat SINGLE* — and the
per-item correctness-disagreement feature has held-out AUC only **0.59** for that axis.
**Booked: can a cheap gate predict the per-item FED−SINGLE accuracy win (not the regime)
at held-out AUC ≥ 0.70 — and does the cheap 325-param logistic two-arm, which already
reproduces the +0.196 negation win at 0 GPU, make COMP1's 4228-param FED MLP unnecessary?**

## Artifacts

- `results/ring_cx2/ring_cx2_results.json` — full receipt (gates a/b/c, T1–T4,
  prevalence-matched protocol, 0-param router baseline, disagreement sensitivities,
  per-regime alert/accuracy, bootstrap refits).
- `experiments/ring_cx2.py` — harness (CPU numpy+sklearn, ~2.3 s wall, 0 Wh, no GPU).

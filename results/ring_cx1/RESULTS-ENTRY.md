# RING-CX-1 — SYNTH-0 wildcard, closing probe: untrained ANSWER-MARGIN-gated ring

**Lane:** RING-CX-1 · **Date:** 2026-10-01 16:24 AKDT · **Seed:** 2718 (+2719..2722 for std)
**Device:** CPU only (numpy) · **GPU:** not used · **Training:** none · **Commit:** none (lane does not commit)
**Reuses:** `experiments/ring_cx0.py` + `results/ring_cx0/repro/` wholesale (resume-not-rebuild).

---

## The question (booked by RING-CX-0 as the next question)

RING-CX-0 FAILed honestly: the untrained *certainty*-gated ring does not see the blind
regime (negation Reject 0.127 = second lowest of four; Reject piles on `semantic`
0.369 — it fires on sensor-key representational flatness). **Does an ANSWER-MARGIN
gate place Reject on `negation-scope`? I.e. is the blind regime visible to ANY
untrained gate, or only to the trained FED−SINGLE disagreement?**

## (1) Wiring harness (unchanged from r0)

Rebuilt the frozen COMP1 word-view featurization (sha1 BoW D=64, L2) + the frozen
0-parameter D13d regime-centroid Pearson router on TRAIN only. Held-out top-1 =
**0.7356**, bit-equal to COMP1's booked `router_audit.heldout_acc` **0.7356**. No labels,
no training, no GPU.

## (2) GATE SWAP — per-sensor ANSWER MARGIN

`cue_s`: r0 `softmax(ρ_s / T)` (routing *certainty*, competition-normalized) →
r1 **per-sensor answer margin**. Sensor cell *s*'s binary self-answer distribution is
`{p_s, 1−p_s}` with `p_s = σ(ρ_s / T)`, so

```
margin_s = |p_top1 − p_top2| = |2·σ(ρ_s / T) − 1|
```

with `T` = **median TRAIN top-1 ρ = 0.7374** (label-free temperature; the margin
doctrine of COMP1/r0). The ring integrates margins **exactly as before** — same N=64
local-excitation/global-inhibition DoD kernel (σE=16°, J_E=5, J_I=1), same α/ticks/L2,
same τ doctrine (**τ = 20th pct of TRAIN R**), same seeded jitter (cue-angle N(0,5°) +
multiplicative lognormal cv=0.10), same robustness-grid shape.

### Structural pre-note (verified before writing the lane)

The ring update is **positively homogeneous** (`relu(c·x) = c·relu(x)`, c ≥ 0), so the
L2-normalized fixed point — and R — depend *only on the direction of the cue vector*, not
its magnitude: `ring.read([0.1,0,0,0]) == ring.read([1,0,0,0]) == 0.6702` **exactly**, and
any all-equal cue vector gives R = 0.0000 at any level. **Consequence:** an answer-margin
gate routed through this ring is *provably* a cue-**shape** gate — it cannot represent
absolute per-sensor decisiveness (level) at all. Pre-registered as specified anyway; the
direct **absolute**-margin gates are reported as labelled exploratory so the "does level
carry the blindness?" question is actually asked.

## (3) GATES (pre-registered, seed 2718)

| gate | statement | measured | verdict |
|---|---|---|---|
| **G-A′** | ring overall acc ≥ trained − 0.02 = 0.7156 | **0.3268 ± 0.0125** | **FAIL** |
| **G-B′** | negation Reject-rate ≥ 2× regime-mean | neg **0.0203** vs mean **0.0257**, ratio **0.789** | **FAIL** |
| **G-C′** | every deciding stat seed-std > 0 | all > 0 (reject 0.001–0.014, acc 0.0125) | **OK** |

**Verdict: FAIL** (G-A′ FAIL, G-B′ FAIL, G-C′ OK). Honest negative, fully receipted.

### Reject-rate by regime (ring on margins, seed-mean ± std)

| regime | Reject-rate | ring R | router top-1 |
|---|---|---|---|
| agent-role | **0.0383 ± 0.0143** | 0.123 | 0.611 |
| counting-address | 0.0259 ± 0.0058 | 0.126 | 0.892 |
| **negation-scope** | 0.0203 ± 0.0128 | 0.125 | 0.703 |
| semantic | 0.0184 ± 0.0057 | 0.125 | 0.759 |

**G-A′ collapse mechanism:** the per-sensor margin is **near-flat** across sensors —
within-item spread (max−min) **0.074** on a base of **0.426**, i.e. the cue vector is
almost uniform. The ring resultant near-collapses (R ≈ 0.125 for *every* regime, vs r0's
0.42–0.53), so the readout θ̂ is noise → routing accuracy falls to **chance** (0.327 ≈
0.29 matched-protocol ≈ 1/4). The margin map is *compressive* exactly where r0's softmax
(with the tiny top1−top2 gap temperature 0.0321) is *sharpening*: σ(ρ/T) sits in its
linear region at ρ ≈ T, so it destroys the routing signal instead of amplifying it.

## (4) Robustness

- **τ-calibration protocol (rules out an inert gate).** r0 calibrates τ on *un-jittered*
  TRAIN R; margin cues are near-uniform, so the inherited multiplicative jitter inflates
  held-out R and the gate goes nearly inert (rejects 2–4 %, not 20 %). Re-calibrated under
  the **same stochastic protocol** as held-out: τ = 0.0671, overall reject **19.66 %** —
  and negation is **still below mean**: neg **0.1757** vs mean **0.1956**, ratio **0.898**,
  top-reject `agent-role` (0.2284). The FAIL is not an inert-gate artifact.
- **T × τ_pct grid (9 cells).** negation is the top-reject regime in **1/9** cells and
  reaches ≥2× in **0/9**. Ratio 0.46–1.53.
- **Five untrained answer-margin definitions** (`routing-softmax top1−top2`,
  `raw-ρ top1−top2`, `signed top1-minus-field`, `abs-sigmoid margin mean`, `abs-sigmoid
  margin min`): **0/5** place Reject on negation (negation rate 0.068–0.108; ratios
  0.36–0.59; negation never top-reject). The FAIL is definition-robust.
- **Direct absolute-margin gate (exploratory).** `mean_s margin_s ≤ τ` (τ = 0.3884):
  reject concentrates on **counting-address 0.525**, then semantic 0.135, negation 0.068,
  agent-role 0.031 (ratio 0.356). `min_s margin_s ≤ τ` (τ = 0.3527): counting 0.475,
  semantic 0.184, negation 0.115, agent 0.037 (ratio 0.566). Even a gate that *can* see
  margin level fires on **counting-address** (regime-atypical items — low affinity with
  the semantic keys), never on the blind regime.

## Verdict

**FAIL.** No untrained gate tested — certainty-shape (r0), margin-shape (r1 primary), or
absolute-margin level (r1 exploratory ×2), or any of 5 margin definitions — places Reject
on `negation-scope`. **The wildcard thread closes negative.**

## The one-line answer (closes the SYNTH-0 wildcard thread)

**Only the *trained* FED−SINGLE disagreement sees the blind regime.** Every untrained
gate is a function of *corpus geometry* (routing certainty, per-sensor answer margin),
and that geometry is blind to the axis COMP1's blind regime lives on — the monolith
sensor's failure to *answer* negation, which is only visible against the labels a trained
arm reads. Structurally stronger: the ring's Reject is **provably scale-invariant** in the
cue vector (homogeneity of relu), so no per-sensor *margin level* can ever reach it; and
even the level-aware absolute gate fires on `counting-address`, i.e. on representational
atypicality, not on blindness.

## Next question

The blind regime is a **label-referenced** property (FED−SINGLE disagreement is computed
from correctness). Untrained geometric statistics are provably the wrong axis. So: is
COMP1's negation win reproducible by a gate that is *trained* but *cheap* — e.g. a single
logistic on the 4 per-sensor margins (or on the 2-arm disagreement) — and does that cheap
trained gate beat the full FED arm for a fraction of the cost (a "wiring gate" in the
COMPOSITE-2 sense)? If yes, book: blindness is detectable, but only *after* labels enter;
cheapness lives in the gate, not in the geometry.

## Artifacts

- `results/ring_cx1/ring_cx1_results.json` — full receipt (gates, matched-protocol
  diagnostic, 9-cell grid, 5-definition robustness, exploratory absolute-margin gates,
  per-seed).
- `experiments/ring_cx1.py` — the harness (CPU numpy, ~12 s wall, 0 Wh).
- Repro lineage: `results/ring_cx0/repro/fly_cx.py` + `fly_cx_receipt.json` (r0, PASS 4/4;
  ring dynamics identical, reused by reference).

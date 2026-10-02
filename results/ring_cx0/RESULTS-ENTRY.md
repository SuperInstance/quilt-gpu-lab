# RING-CX-0 — SYNTH-0 wildcard: training-free certainty-gated ring attractor as router

**Lane:** RING-CX-0 · **Date:** 2026-10-01 16:14 AKDT · **Seed:** 2718 (+2719..2722 for std)
**Device:** CPU only (numpy) · **GPU:** not used · **Training:** none · **Commit:** none (lane does not commit)

---

## The question

COMP1 (`results/comp1/`) booked that federation beats a monolith **only where the
monolith sensor is structurally blind**: negation-regime FED−SINGLE **+0.1261
CI[+0.0338,+0.2185]**, full board flat (+0.0102, CI spans 0), floor effect 0.547–0.562
on 0.5169 chance. SYNTH-0 asks: **can a routing mechanism that is never trained SEE
that blind regime through its Reject dynamics?**

## (1) REPRO — harvested fly-CX ring attractor

- **Source (exact file):** `pr_harvest/_raw/chiaroscuro_6.diff` → hunks
  `diff --git a/tools/fly_cx.py` (chiaroscuro #6, **flycx v2 certainty-gated**,
  169 lines). This is the harvest's *only PASS cluster* (SUMMARY.md §1:
  "the one cluster with a **PASS** (flycx 4/4)").
- **Action:** verbatim extraction (strip `+`) → `results/ring_cx0/repro/fly_cx.py`,
  run unchanged. **pr_harvest DOES contain runnable code — no first-principles port needed.**
- **Receipt:** `results/ring_cx0/repro/fly_cx_receipt.json`
  - T1 zero-drift `0.0°/s` PASS · T2 consistent anchor `err 0.007°` PASS
  - T3 conflict-reject `amp_drop 0.3000` (= REJECT_SHRINK exactly), `θ disp 0.0°` PASS
  - T4 dark-hold `0.0°` PASS · null control (ψ forced +1) `71.999° > 60` PASS
  - **verdict PASS 4/4**, trajectory `fnv1a64 = 41c8af26ba55cb03`
- **Core dynamics reproduced standalone:** bump (θ, A) + certainty-gated capture
  (`θ += BLEND·(1−A)·err` on conflict) + `A *= 0.7` reject shrink + dark-hold.

## (2) WIRING — per-item per-sensor confidence from EXISTING COMP1 artifacts

No re-training, no GPU. From `results/comp1/corpus.jsonl` (2400 items, sha256-split
1810 train / 590 held-out, reproduced exactly) I rebuilt the **frozen COMP1
featurization** (word view: lowercase alnum-token BoW, sha1→D=64, L2) and the
**frozen 0-parameter D13d regime-centroid Pearson router** (train-only keys).
Per item → 4 sensor scores → confidence `softmax(score / T)`.

**Wiring validation:** reproduced router held-out top-1 = **0.7356**, bit-equal to
COMP1's booked `router_audit.heldout_acc` **0.7356**. Call it a wiring bill of health.

**Ring (primary engine):** N=64 head-direction-style continuous attractor.
`K_ij` row-normalized Gaussian(σE=16°), `W = J_E·K − J_I` (local excitation /
global inhibition), cue injection `I_i = C·Σ_s conf_s·Gauss(φ_i; 90s, 30°)`,
`r ← (1−α)r + α·relu(Wr+I)`, L2-normalized (shape-only) × 60 ticks.
Readout = circular mean → θ̂ and certainty `R = |resultant|`.
**Gate:** item REJECTS iff `R ≤ τ_ring`, `τ_ring` = 20th pct of TRAIN R (COMP1's own τ doctrine).

*Label-free kernel selection (fixed before any accuracy was seen):* among all
(σE, J_E, J_I) giving flat-input `R = 0.000`, take the plateau-median config →
σE=16, J_E=5, J_I=1 → `R_flat = 0.0000`, `R_single-cue = 0.6702`. No label or
accuracy entered the choice. `T` = median TRAIN top1−top2 gap = 0.0321 (COMP1's margin doctrine).
Seeded jitter (cue-angle N(0,5°) + conf lognormal cv=0.10) supplies the seed-std the frost law needs.

**Engine B (cross-check):** analytic fly_cx v2 with the **harvested constants verbatim**
(τ_motion=.35, CONFLICT_DEG=30°, REJECT_SHRINK=.7, A0=.5) on the same discrete cues.

## (3) GATES (pre-registered, seed 2718)

| gate | statement | measured | verdict |
|---|---|---|---|
| **G-A** | ring overall routing acc ≥ trained − 0.02 = 0.7156 | **0.6224 ± 0.0042** | **FAIL** |
| **G-A′** | (reading: accuracy conditional on commit) | **0.7800 ± 0.0057** | *(above threshold)* |
| **G-B** | negation Reject-rate ≥ 2× mean across regimes | neg **0.1270** vs mean **0.2065**, ratio **0.615** | **FAIL** |
| **G-C** | every deciding stat seed-std > 0 | all > 0 (reject 0.003–0.017; acc 0.0042) | **OK** |

### Reject-rate by regime (ring, seed-mean ± std)

| regime | Reject-rate | ring certainty R | router top-1 |
|---|---|---|---|
| semantic | **0.3688 ± 0.0168** | 0.420 | 0.759 |
| counting-address | 0.2216 ± 0.0115 | 0.526 | 0.892 |
| **negation-scope** | **0.1270 ± 0.0079** | 0.490 | 0.703 |
| agent-role | 0.1086 ± 0.0030 | 0.497 | 0.611 |

**The blind regime is the *second-least*-rejected regime.** Reject concentrates on
`semantic` (the ring's least-certain regime), not on `negation-scope`.

**G-B sensitivity (knob check):** ratio 0.49–1.00 across T ∈ {0.02, 0.0321, 0.05} ×
τ_pct ∈ {10,20,30}; `semantic` is the top-reject regime in **8/9** cells. The FAIL is
not a hidden-knob artifact.

### Engine B (harvested constants, verbatim) — a booked failure

On discrete 4-way cues the continuous-compass constants do not transfer unscaled:
reject rates **counting 1.000 / agent 0.982 / negation 0.966** (±0.000–0.014) vs
semantic 0.170. Any two distinct sensors are 90° apart > CONFLICT_DEG = 30° ⇒
every non-current cue is a conflict ⇒ amplitude collapses. The harvested constant set
is a *continuous-compass* parameterization; the 4-way discrete routing instantiation
needs the conflict radius rescaled to the sensor Voronoi half-width (45°). **Booked fact.**

## Verdict

**FAIL** (G-A FAIL, G-B FAIL, G-C OK). Honest negative, fully receipted.

## The one-line answer

**No** — the untrained certainty-gated ring does **not** see the blind regime through
its Reject dynamics: Reject-rate in `negation-scope` is **0.127**, the *second lowest*
of four regimes, while Reject piles up on `semantic` (0.369). Routing selectivity and
task competence are dissociated: the monolith sensor is blind *at answering* the
negation board while the routing signal for that regime is comparatively *sharp*
(router top-1 0.703 there, and its 0.490 ring certainty is mid-pack) — the ring's
Reject fires on *representational flatness of the sensor keys*, which is a property of
the corpus geometry, not of the federation's blindness.

## Next question

If Reject tracks corpus-geometry flatness rather than task blindness, does an
**answer-margin** gated ring (per-sensor *cell* margin from a cheap probe, not router
correlation) place Reject on `negation-scope`? I.e. is the blind regime visible to any
untrained gate at all, or only to the *trained* disagreement between FED and SINGLE?

## Artifacts

- `results/ring_cx0/ring_cx0_results.json` — full receipt + per-seed + sensitivity
- `results/ring_cx0/repro/fly_cx.py` + `fly_cx_receipt.json` — harvested repro
- `experiments/ring_cx0.py` — the harness (CPU, ~3 s wall)

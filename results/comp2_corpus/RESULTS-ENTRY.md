# COMPOSITE-2 phase 1 — corpus build + F-gate calibration (lane COMPOSITE-2-BUILD)

**Ran:** 2026-10-01 17:2x AKDT · `experiments/comp2_corpus_gate.py`
**Prereg:** `proposals/runs/COMPOSITE-2-federation3.md` (frozen 17:2x, read as the spec)
**Scope:** phase 1 ONLY — corpus build + F-gate calibration. **Arms are BLOCKED in phase 1**; no arm
was trained, no GPU was touched, no commit made.
**Cost:** CPU-only, **0 Wh**, no GPU, no torch. Wall ≈ 25 s per full calibration pass (6 iterations
× 24,600-item corpus gen + logistic probe). The prereg's "~2 min corpus gen" estimate was 10×
conservative.

## VERDICT — F-GATE GREEN · corpus FROZEN · **ARMS UNBLOCKED**

The F-gate landed **GREEN at iteration 5 of 8** (6 iterations executed). The COMPOSITE-2 corpus is
frozen with a logistic linear probe on the frozen S1 word64 view at:

| board | reading | band | margin |
|---|---|---|---|
| **full** | **0.7164** | [0.65, 0.85] | +0.043 / −0.134 |
| semantic | 0.8611 | [0.60, 0.90] | +0.261 / −0.039 |
| counting-address | 0.6545 | [0.60, 0.90] | +0.055 |
| **negation-scope** (blind regime) | **0.6288** | [0.60, 0.90] | **+0.029** (binding) |
| agent-role | 0.7187 | [0.60, 0.90] | +0.119 |
| refit std (full) | **0.001266** | > 0 | ✓ non-degenerate |

Frozen knobs: **k1 near_miss = 2.312 · k2 β = 0.35 · k3 vocab_frac = 1.0 · k4 style_mix = 0.5**
(i.e. COMP1-A1 grammar verbatim, with k1 the only knob moved). Per-regime refit stds all > 0
(0.0009–0.0060). The **binding constraint was negation-scope ≥ 0.60** — the structurally blind
regime is also the hardest for the BoW probe, which is exactly the regime the thesis is about.

## 1. Corpus (N=24,600 raw; frozen spec)

- **n_raw 24,600** (6,150/regime), **dedup exact-unique 24,600** ✓, **LCG regen collisions 199**
  (deterministic regeneration exercised), overlay rate **0.3569** (≈ β 0.35).
- **split (COMP1/D5 law, first sha256 nibble ≥ 0xC → held-out):** train **18,379** / held-out
  **6,221** (semantic 1,579 · counting 1,587 · negation 1,523 · agent 1,532).
- **validity gates all pass** (`validity_ok: true`): n_heldout 6,221 ≥ 5,600 ✓ · every per-regime
  held-out ≥ 1,523 ≥ 1,350 ✓ · |canon frac − 0.5| = 0.0068 ≤ 0.06 full and ≤ 0.033 per-regime ✓ ·
  dedup exact-unique ✓ · determinism re-gen identical (W1) ✓.
- **corpus sha256-sequence** `5bc6b78f0a4b59481a4e4cc023db743d29bdd9a6db817116332b9e131bf1a3fa`
  (7,584,332 bytes).
- **Grammar = COMP1-A1 VERBATIM — receipt, not assertion:** `gen_item_c2` was driven against
  COMP1's own `gen_item` on independent copies of the same LCG stream at default knobs:
  **1600/1600 items byte-identical, 0 mismatches.** Featurization/renderer/LCG/sha256 split are
  imported from `experiments.comp1_federation2` (no re-implementation). Determinism W1: two
  regenerations produce identical sha256 sequences.
- **near-miss distance** (measured corpus statistic, mean claim↔evidence token-set Jaccard):
  trajectory 0.6044 → 0.6351 → 0.6205 → 0.6281 → **0.6244 (frozen)** → 0.6221.

## 2. F-gate calibration loop (6 of ≤8 iterations)

Search = adaptive bisection on **k1 near-miss distance**, the dominant dial (k2/k3/k4 declared and
available; k2 was the r1 fallback but was not needed for the final freeze).

| it | k1 nm | β | full | semantic | counting | negation | agent | verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | 2.000 | 0.35 | 0.6792 | 0.8184 | 0.6246 | **0.5612** | 0.7132 | VIOLATION (neg < 0.60) |
| 2 | 2.500 | 0.35 | 0.7430 | 0.8607 | 0.6886 | 0.6780 | 0.7551 | GREEN |
| 3 | 2.250 | 0.35 | 0.6987 | 0.8398 | 0.6239 | 0.6075 | 0.7226 | GREEN (inside margin rule) |
| 4 | 2.375 | 0.35 | 0.7241 | 0.8630 | 0.6579 | 0.6403 | 0.7356 | GREEN |
| **5** | **2.312** | **0.35** | **0.7164** | **0.8611** | **0.6545** | **0.6288** | **0.7187** | **GREEN — FROZEN** |
| 6 | 2.281 | 0.35 | 0.7093 | 0.8515 | 0.6415 | 0.6148 | 0.7293 | GREEN (raw band), below margin rule |

Only **k1** was moved in the final freeze; β was left at COMP1's 0.35, and k3/k4 at COMP1 defaults —
so the frozen corpus is **COMP1-A1 grammar with a single declared difficulty knob** (expected number
of regime-relevant evidence fields perturbed on a distortion; 1.0 = COMP1 verbatim).

### Harness revisions (disclosed; archived, not deleted)
- **r1 → `calibration_log.harness-invalid-r1.json`** (+ corpus/stub). The bisection inspected only the
  **full board** to pick direction, so when a **per-regime lower bound** was the binding constraint it
  classified "negation too hard" as "too easy" and walked the wrong way. It still returned GREEN, but at
  full **0.8485 (cap 0.85)** and semantic/agent **0.892 (cap 0.90)** — a top-of-band knife-edge, not
  mid-band. Harness-invalid (COMP1 r1 precedent): re-fired, spec unchanged.
- **r2 → `calibration_log.r2-minimal-edge.json`** (+ corpus/stub). Correct multi-constraint direction;
  froze at the *minimal* feasible near-miss (nm 2.188, full 0.6933) — but its binding reading was
  negation-scope **0.6039 vs the 0.60 floor, within ~1.3σ of the refit noise (0.0033)**. A green that is
  a coin flip does not *establish* mid-band difficulty, which is the F-gate's whole purpose.
- **r3 (booked).** Declared robustness margin: every bound must be cleared by
  **max(0.02, 5×refit-std)**. This encodes the prereg's stated prerequisite ("mid-band difficulty is the
  C2 prerequisite") rather than edge-of-feasibility. Frozen point clears its binding bound by **0.0288**
  (≈ 5× the required margin, ≈ 24× the negation refit std).

## 3. Per-item persistence (booked law — CX-CHEAP-0 lesson)

`per_item_stub.jsonl` — **24,600 rows, one per corpus item**, keyed `{key, sha256, regime, label,
split}` with the downstream prediction fields **present and null** (`p, correct, margin,
routed_sensor, cell, la_trigger, la_flip`). The structure every arm × seed × item prediction must
populate is fixed now, before any arm exists — so no downstream artifact can again force a re-derivation.

## 4. Artifacts

`results/comp2_corpus/` → `corpus.jsonl` (24,600) · `per_item_stub.jsonl` (24,600) ·
`calibration_log.json` (every iteration: knobs, full + per-regime readings, refit lists, refit std,
near-miss distance, validity, required margin, min bound clearance) · `verify_receipt.json`
(grammar-verbatim + W1 determinism) · `pilot_sweep.json` (disclosed small-N direction-finding, **not**
counted against the ≤8 gate budget) · archived r1/r2 logs + corpora.
Code: `experiments/comp2_corpus_gate.py`. **NOT COMMITTED.**

## 5. What phase 1 establishes, and what it does not

**Establishes:** COMPOSITE-2's corpus is mid-band (full 0.7164) with the blind regime (negation-scope)
inside the band at 0.6288 and, critically, **linearly learnable at all** — unlike COMP1's corpus, where
the probe sat at 0.527 full and negation *below chance* (0.446). The floor effect that killed COMP1's
full-board is repaired: the corpus is now difficulty-wired before any arm fires.

**Does not establish anything about the thesis.** No arm was trained; P1–P4 are untouched. The gate
also reveals the corpus's own tension, worth carrying forward: **negation-scope is simultaneously the
thesis's blind regime and the corpus's hardest regime** — the two hardest knobs are the same knob, so
the near-miss dial buys negation accuracy only by also pushing semantic toward its 0.90 ceiling
(semantic 0.8611 at the freeze). If the arms' negation effect turns out to be an artifact of *general*
difficulty, S4-MONO (§Risks 4) is the control that can say so.

## 6. RETRY-r1 independent re-verification (2026-10-01 17:4x AKDT)

The lane was re-dispatched as a retry under the belief that the prior attempt had died before doing
any work. **It had not** — the artifacts above were already on disk and booked. Rather than clobber
valid work, the retry lane re-verified it **read-only** (no regeneration, no writes to any booked
file): `scratch/comp2_verify_r1.py` → `results/comp2_corpus/verify_r1_independent.json`.

**21/21 checks PASS.** The decisive one: the F-gate was **recomputed from the persisted
`corpus.jsonl`** (loaded, split by hash nibble, refit) and reproduces the booked boards *exactly* —
full **0.7164**, semantic 0.8611 · counting-address 0.6545 · negation-scope 0.6288 · agent-role
0.7187, std 0.001266 — so the gate is a property of the frozen corpus, not of a regeneration.
Corpus sha256-sequence matches `5bc6b78f…`; 24,600 dedup-unique; split 18,379/6,221 (per-regime
≥1,523); `per_item_stub.jsonl` 24,600 rows with a uniform key set and all prediction fields null;
grammar-verbatim 1600/1600; W1 determinism identical; **arms remain BLOCKED**
(`results/comp2/predictions` and `results/comp2/guard` absent). Booking unchanged; nothing committed.

**Next question.** With the corpus frozen and arms unblocked: fire the 6 MLP banks × 3 seeds under the
G7 guard (≤20 Wh envelope, INSTRUMENT-01 ramp receipt) and read **P1 (FED-HETERO − SINGLE @negation-scope
≥ +0.08, CI_low > 0)** — does a heterogeneous-SENSOR bank beat the single cell on the blind regime of a
corpus where the blind regime is no longer a floor? Pre-registered follow-up inside the same lane: does
S4-MONO alone match FED-HETERO (§Risks 4 re-read), which would narrow the thesis to "buy the right
sensor once"?

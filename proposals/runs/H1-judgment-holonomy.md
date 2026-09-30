# H1 — Judgment Holonomy Audit (CPU)

**Status:** PRE-REGISTERED, frozen before fire. 2026-09-30, ~09:26 AKDT.
**Runners:** `experiments/h1_judgment_holonomy.py` · **Results:** `results/h1_judgment_holonomy/results.json`
**Lane:** wide-scope #3 (judgment holonomy) — first falsifiable probe.

## Question

Can loop-inconsistency (holonomy over tictactoe's symmetry gauge group) localize a field's
blind region **with zero teacher calls during the audit**, and does it beat the plain
neighborhood-uncertainty baseline (kNN margin)? This is the cheap gate that decides whether
holonomy is a real organ (free audit + free curriculum) or just neighborhood noise rebranded.

## Construction

- Field: 1200 tictactoe positions sampled from random playouts, each labeled by the true
  minimax outcome (solver used ONLY to build/corrupt the corpus — never during scoring).
- Rooms: 27-dim one-hot board → seeded random projection to 16-d. Field judgment = kNN
  (k=9, inverse-distance weights) vote over stored labels {+1,0,−1}.
- Blind region: per seed, a marker pattern P = TWO cells with fixed marks (X at cell a,
  O at cell b; a≠b, placement seeded); every field episode matching P has its stored label
  **flipped** (guaranteed wrong). Expected corrupted count recorded; must be ≥ 40 or the seed
  is void (re-drawn). [AMENDED PRE-FIRE 09:2x, before any fire: the original 3-cell X/O/X
  pattern voids every seed (smoke 0/2) — ~3.7% base rate vs the ≥40/1200 bar. Two cells
  (~11%) clears it. Amendment committed before fire; no other gate touched.]
- Holonomy score (teacher-free): for a probe board b, take its 8 symmetry images; grade each
  with the field; inconsistency(b) = entropy of the 8 predicted outcome classes (0 = all
  images agree, ln3 = maximal disagreement). Probe set: 600 fresh boards (300 matching P,
  300 clean, balanced by construction).
- Baseline score (teacher-free): leave-one-out kNN margin on b itself (lower margin =
  more uncertain). The honest comparison: does the symmetry loop add signal beyond plain
  neighborhood uncertainty?

## Frozen gates (decided before fire)

- **KEEP** for the holonomy claim iff, on ≥ 4/5 seeds:
  AUC(holonomy separating corrupted-vs-clean probes) ≥ 0.80 **AND** paired
  AUC(holonomy) > AUC(margin baseline).
- **KILL** otherwise. If holonomy ≈ baseline (AUC gap < 0.02 in mean), verdict is
  **INDIFFERENT** (recorded honestly — the loop adds nothing, use plain margin).
- No post-hoc score tweaks, no added probes after fire, no seed re-rolls beyond void rule.

## Seeds

7711, 7712, 7713, 7714, 7715 (position samples, projection, pattern placement, probe draws).

## Failure handling

Smoke first (2 seeds, reduced counts). Fail loud on any NaN/degenerate field. No retries on
provider errors (no provider used). Book honestly whatever lands.

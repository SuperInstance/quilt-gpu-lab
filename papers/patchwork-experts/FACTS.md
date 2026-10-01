# FACTS DOSSIER — verified numbers for the patchwork-experts paper

Every number below was produced this session (2026-09-30) and is committed in this repo.
A paper draft may use ONLY these numbers or numbers read directly from the cited results
files. Anything else must be marked [CITE-MISSING]. Do not round differently than shown.

## Terrain (ground truth)
- SuperInstance/pie-minimax @ main, exact minimax solver, read-only clone.
- 180,361 our-turn reachable states. Provenance FNV-1a-64 over (state + optimal-set) stream:
  `0x75f652bc1d8464b8`. Representation: 9 floats (raw board, row-major). Labels = optimal-move sets.
- Metric everywhere: top1-in-optimal (argmax ∈ optimal set) + set-recall, always reported together.
- PX1 seed-0 split: 80/20 → 144,288 train / 36,073 test. Trees: sklearn DecisionTreeRegressor,
  min_samples_leaf=5, random_state=seed. Trained on TRAIN split only, always.

## PX1 — decision-tree ceiling (results/px1_tree_ceiling/results.json)
- Deep tree (unbounded): 0.9987 ± 0.0002 → the ceiling is the exact function.
- Linear (pie-minimax's own linear_expert, same representation): 0.1978 ± 0.005.
- Depth ladder: d3 0.4811, d4 0.6024, d6 0.7481.
- P3 surprise: linear on SIMPLE states (0-1 immediate wins) 0.1895 vs COMPOSED (≥2 immediate wins)
  0.2640 — additive voting is FINE where multiple wins exist.

## PX1b — threat-locality partition (results/px1b_threat_locality/results.json)
- Frozen classes, digest `0xa0b08dfac4d13c57`: WIN 109,392 (60.6%) = immediate win available;
  BLOCK 29,632 (16.4%) = opponent 2-in-line, all opt are blocks; NON_LOCAL 41,337 (22.9%) = rest.
- Per-class top1 (test, 3 seeds): WIN — linear 0.25 / d3 0.55 / d6 0.84 / deep 0.9998.
  BLOCK — linear 0.022 ± 0.003 / d3 0.24 / d6 0.57 / deep 0.997.
  NON_LOCAL — linear 0.17 / d3 0.49 / d6 0.64 / deep 0.996.
- Mechanism: additive voting dies on DEFENSE (the defensive override), not on non-local play.
  Design consequence: composed systems need VETO primitives (gates/pinchers), not better voters.

## PX2 — patchwork harness + gardener (results/px2_patchwork/*)
- Composed d3+d4 majority-vote with format gate: 0.595 vs d3-alone 0.435 (frozen 200-state eval).
- Full-roster composition (trees d1..d6 + pinch, MajorityVote): **0.7437 top1 on the full 36,073-state
  test split** (measured in PX5).
- Cells: trees (depth k, TRAIN-only), PinchCell (center-if-empty-else-block, abstains otherwise),
  FormatGate (9-finite-float structural gate), MajorityVote (argmax votes, tie→lowest index).
- Immune layer (per PX0 three-model convergence): sanity cell 5/5 gate before session; 5% seeded
  shadow no-ops logged sidecar-only; fixed-1k drift re-check every 10 moves; BLOCK split every eval.
- Blind gardener (seeded RNG legal moves): seed-0 10 moves → 0.855 (lucky tail);
  budget-matched 50-move seeds 1/2/3 → 0.745 / 0.745 / 0.755 (mean 0.748, spread 0.010).
  Blind walk has no ratchet — endpoint ≠ best-seen.
- Live GLM-5.3 gardener (coding-plan endpoint): fires 1-4 aborted fail-loud; diagnosis chain from
  abstain receipts only: thinking ate 400-token budget → adaptive thinking ignores the disabled flag
  (17k-char reasoning, finish_reason=length at 4096) → 120s read timeout. Fixes: 16384 cap, 240s
  timeout, transport-failures-as-receipted-abstains, one clean same-prompt retry (no outcome info seen).
  Fire 5 in flight at dossier time — paper should cite its FINAL adjudicated numbers only
  (from results/px2_patchwork/ once booked), else mark [CITE-MISSING].

## PX3 — judge distillation (results/px3_distill/px3_result.json)
- selectlib's judge = typesafe api `/v1/systemone`, model jev-1.13.0, choice criteria
  correct/needs_fix. 576/576 calls, 0 errors, receipts digest `0x29ebeffdce727a44`.
- Reproduction: noise+oracle MAEs bit-exact vs stored run (harness identical);
  BLIND_UNIFORM deltas +0.0000 ×3 exact; BLIND_SPLIT judge deltas drifted magnitude-only
  (direction holds) → cross-run MODEL-side drift; within-run duplicate-triple consistency 1.0.
- Evals (numpy logistic head on local nomic-embed-text 768-d embeddings of state strings):
  within-SPLIT 0.9583 (F1 0.50/0.98, only 3 correct-class states); within-UNIFORM 1.0 (trivial);
  cross-field split→uniform 0.9167, CI [0.854, 0.969] — lands in the frozen WIN zone (≥0.85)
  BUT uniform test labels are single-class (96/96 needs_fix) → degeneracy guard → INCONCLUSIVE.
- Mechanism discovery: the judge is ~a constant function on both blind fields
  (93/96 and 96/96 needs_fix) — this is WHY the stored result says judge ≈ noise: a nearly-constant
  label function carries no structural signal. A constant-baseline check is mandatory for any
  LLM-as-judge distillation.
- Second instrument-drift finding: stored UNIFORM free-statistic corr −0.184 irreproducible
  (fresh −0.156) on an offline-deterministic quantity → stored line predates final fields.py.

## PX5 — cell-signature map (results/px5_disagreement/px5_map.json)
- Instrument: per test state, 6-bit signature (which trees d1..d6 place top1 in optimal set)
  × pinch axis (fired-correct / fired-wrong / abstain) × px1b class × composition-correct.
  EXPLORATORY_MAP pre-reg frozen commit-first (ecc8288) before scoring.
- 15 unique signatures across 36,073 states (64 possible).
- MI(signature → composition-correct) = 0.5955 bits; MI(signature → class) = 0.1212 bits.
  → the between-cell routing surface strongly predicts composition success and is nearly
  orthogonal to the author-chosen threat taxonomy (a latent taxonomy discovered, not authored).
- Unanimous partitions: all-6-correct 9,470 (26.3%) — reflex-compile candidates;
  all-6-wrong 7,895 (21.9%) — class-blind failure basin, spread WIN 2812 / BLOCK 2392 / NON_LOCAL 2691.
- Router ceiling (any-cell-correct incl. pinch): 0.8698 overall vs composition 0.7437 → +12.6pts headroom.
- Pinch pre-emption: fires on 72.5% of states (66.35% correct / 6.15% wrong), abstains 27.5%.

## PX0 — ideation convergence (results/px0_ideation/round1.md)
- Seed-2.0-mini, Hermes-3-405B, tencent/Hy3 independently located silent-failure risk in
  GARDENER EPISTEMICS (format-pass/semantic-broken; drift; post-hoc rationalization) and proposed
  controls that composed into the PX2 immune layer. Cite as the design-origin receipt.

## Honesty requirements for the paper
- Pre-registration discipline: PX1/PX1b (docstring-frozen), PX2 (file-frozen), PX3/PX5
  (commit-first frozen). PX1b deviation (post-hoc commit) is disclosed in RESULTS.md — keep that
  disclosure in the paper; it is part of the method story.
- Blind-control correction narrative (lucky tail → budget-matched distribution) stays in.
- Branch rulings reported as-ruled: PX2 pending final adjudication; PX3 INCONCLUSIVE with guard.
- Limitations must include: single microcosm domain; exact-solver luxury not available in most
  real tasks; jev-constancy shown on two synthetic fields only; router headroom measured, not yet claimed.

# K1 — plan (worker contract, written before build)
*In-house continuation: the dispatched lane died in the 2026-09-28 rate-limit storm
before writing its plan. Spec frozen earlier in docs/keel-backcast-2026-09-28.md §4;
this plan restates it verbatim. baseline_revision pinned at fire time.*

## Question (the keel's first rung)
Does predicting LATENT DIFFERENCES beat predicting LATENT STATES on frozen
V-JEPA 2 latents, matched capacity, matched readers?

## Design
- **Stage 0 (`k1_cache.py`, ≤25 min):** encode deterministic glyph-lattice clips
  (drifting fields; per-clip (vx,vy) stored → 4-quadrant motion labels = the 4-code
  arity) with V-JEPA 2 (`facebook/vjepa2-vitl-fpc16-256-ssv2`, HF cache present).
  Defensive loader (E7 module introspect → torch.hub fallback). HARD preflight:
  one clip, assert shape/finiteness — die in seconds, not a 2h burn.
- **Arms (4):** {diff-target, state-target} × {seed 42, seed 1337}.
  Predictor: D→512 proj, 2 causal self-attn blocks (d=512), head 512→D.
  state arm predicts z_{t+1} directly; diff arm predicts z_{t+1}−z_t.
  **Both arms scored identically: reconstruction MSE against z_{t+1}**
  (diff arm reconstructs as pred_diff + z_t). Same steps, LR, batch, windows (K=8).
- **Baselines/readers:** persistence (ẑ_{t+1} := z_t). Readers on reconstructed
  latents: ridge (closed-form) + MLP, predicting the 4-quadrant motion label.
- **Budget:** ≤2h. `~/venvs/elephant-gpu/bin/python`. Fire under
  `chip_route --class tensor` + `.gpu.lock` + verified-fire chain.

## Gates (frozen — pre-registered; never loosen mid-run)
- **KEEP iff:** diff beats state by ≥0.05 relative (val reconstruction MSE) at
  BOTH seeds AND both arms beat persistence.
- **KILL iff:** state ≥ diff pooled paired, with healthy harness (all arms beat
  persistence, losses finite/sane).
- **INCONCLUSIVE (K-G5 reader rule):** any win that appears ONLY under the MLP
  reader (linear-reader blind) = INCONCLUSIVE, not KEEP.
- **INVALID_HARNESS:** any arm fails persistence / encoder preflight fails /
  non-finite losses. Escapes are for harness bugs, never for weak results.

## Receipts
- `training/keel_k1/results/k1_results.json` — all arms × seeds, persistence,
  both readers, verdict computed in-script against these exact gates.
- RESULTS.md dated block from script stdout. Time-capsule commit, pathspec-scoped, pushed.

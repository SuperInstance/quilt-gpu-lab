# ternary_transition_kernel

## WHAT IT DOES

The relational transition kernel — the "Transitional JEPA" primitive — as a
standalone block: a multi-agent field world whose transitions are LINEAR in
the field state, plus the closed-form arm harness that proves the perceptual
feature for predicting a transition is the TERNARY correlation of the acting
pair's identity streams — `sign(id_src - id_tgt)` with a deadband, values in
{-1, 0, +1} — not the continuous difference. In one sentence: **it maps
continuous relational state to a 3-symbol codec and proves nothing
predictive is lost.**

Generator: `field_after = 0.5 * field_before + push * normalize(id_src -
id_tgt) + eps`. The world (`FieldWorld`) reproduces the D19 draw stream
bit-for-bit (same rng call order and sizes as
`tools/transition_kernel.make_tripartite_transitions`), so a fresh seed-2718
world matches the booked ledger to ~4e-6 on the solver-stable arms.

Harvested from `tools/transition_kernel.py` +
`experiments/d19_transitional_jepa.py` + `experiments/d20_transitional_ablate.py`;
receipt of record RESULTS.md D19 + D20 (2026-09-27, seed 2718).

The block carries one booked numerical law every consumer must know: **the
oracle arm is rank-deficient BY CONSTRUCTION** — its diff_n rows are
differences of only n_agents=8 identity vectors, so its feature columns span
≤ 7 directions (measured rank 40 of 65) and its held-out MSE wobbles ~1e-3
across solvers/precisions (float64 ridge 0.01007, float64 min-norm lstsq
0.01012, float32 lstsq 0.01108, the 2026-09-27 machine's float32 booking
0.01098). The ternary arm (exactly {-1,0,1}) and markov1/shuffled are
solver-stable to ~4e-6. Hence the cost gate is judged at the booked
`COST_TOL = 1e-3` (the oracle's cross-solver wobble, ~100x smaller than the
signal gain) — the honest statement of "ternarization is free" is
**"cost ~ 0, far inside solver noise"**, not a signed digit.

Environment: numpy + stdlib only, no repo-internal imports. CPU-only
(self-test: ~2 s wall). Deterministic, seed 2718 default.

## INTERFACE

- **`ternary_corr(a, b, deadband=0.15) -> int8[d]`** — the codec itself:
  `sign(a-b)` with dims within ±deadband read 0 (near-equal = "no signal",
  not noise). The reusable {-1,0,+1} mapper, usable standalone.
- **`FieldWorld(n_agents=8, field_dim=32, seed=2718, push=0.5, noise=0.1,
  batch_size=4000, edge_source=None)`** — the world. `.step() ->
  TransitionRecord` (fields: `step_index, src, tgt, field_before,
  field_after, ternary_corr, continuous_diff`); `.ids` = persistent
  per-agent identities. `edge_source: callable(step_index) -> (src, tgt)`
  is the composition hook for a discovered-edge upstream (self-edges and
  out-of-range indices raise `KernelError`; a None edge_source draws random
  pairs exactly like D19).
- **`kernel_features(record, feature=None)`** — assemble `[field_before,
  feature, 1]` (trailing 1 = ridge bias column); `feature=None` is the
  markov1 floor.
- **`KernelArm(name, feature_fn=None, shuffle=False)`** + the booked
  registry `BUILTIN_FEATURE_FNS`: `markov1` (no relational feature),
  `ternary` (the kernel), `oracle_continuous` (privileged continuous diff —
  reference only, never the percept), `shuffled` (ternary feature,
  row-permuted — the negative control that must collapse to the markov1
  floor), `nonlinear_quadratic` / `identity_onehot` (D20 ablations).
  Unknown names raise `UnknownArmError`; duplicate names in one run raise
  `KernelError`; a `feature_fn` override keeps the booked name (typos fail
  loud).
- **`run_arms(world, arms, train_steps, holdout_steps, seed=2718,
  lam=1e-6) -> receipt dict`** — draw n = train+holdout transitions, fit
  every arm by closed-form ridge (`ridge_fit`, bias column unpenalized),
  score held-out MSE. The receipt carries `heldout_mse`, `signal_gain`
  (markov1 − ternary), `ternarization_cost` (ternary − oracle; booked
  convention: negative = ternary beats oracle), `control_band` /
  `control_ok` (shuffled ≈ markov1 within max(2e-3, 15% of markov1)).
  Fail-loud: `NonFiniteMSEError` on NaN/inf, `SignalLeakError` if the
  shuffled control BEATS ternary (the "signal" would be a leak).
- **`judge(receipt) -> {"verdict": "KEEP"|"KILL", "reason": str}`** — the
  FROZEN ordering, no goalpost migration: `ternarization_cost <= COST_TOL`
  AND `signal_gain > 0` AND shuffled within the control band. The cost gate
  is the booked tolerance, NOT a hard `ternary <= oracle` — the oracle arm
  is the rank-deficient design whose MSE is solver-dependent (see above).
- **`control_band(markov1_mse)`**, constants `DEADBAND=0.15`,
  `RIDGE_LAM=1e-6`, `COST_TOL=1e-3`, `CONTROL_BAND_ABS=2e-3`,
  `CONTROL_BAND_REL=0.15`, `ABLATION_REL_GATE=0.02`,
  `HEADLINE_SEEDS=(2718, 2719, 2720)`, `BOOKED_D19` (the ledger anchor).
- **Exceptions:** `KernelError` base; `UnknownArmError`,
  `NonFiniteMSEError`, `SignalLeakError` subclass it.

**House contracts baked in:** seed 2718 default everywhere · self-test final
stdout line is exactly one JSON object with exactly one top-level `verdict`
field (KEEP/KILL/INCONCLUSIVE), exit 0 iff KEEP · headline comparison runs
≥ 3 seeds and any cross-seed std == 0 is booked → INCONCLUSIVE, never PASS ·
fail loud via booked exceptions · no subprocess (if ever added: list-form
only, never `shell=True`) · never reads or prints secrets.

## THE RECEIPT

- Cite: **RESULTS.md D19 (2026-09-27 21:37, KEEP)** lines 831–850 and
  **D20 (2026-09-27 21:41, KEEP)** lines 853–871; code
  `tools/transition_kernel.py`, `experiments/d19_transitional_jepa.py`,
  `experiments/d20_transitional_ablate.py`.
- **D19 booked (seed 2718, held-out MSE):** markov1 0.01786 · jepa_ternary
  0.01012 · oracle_continuous 0.01098 · jepa_shuffled 0.01801 ·
  signal_gain +0.00774 · ternarization_cost −0.00085 · control_ok true.
  Finding 1 (KEEP): ternary correlation of the acting edge carries real
  signal; the shuffled control collapses to the markov1 floor, so the win
  is signal, not capacity. Finding 2: ternarization is FREE — the booked
  −0.00085 is float32 truncation noise on the collinear oracle design (see
  the numerical note; well-posed float64 gives cost ≈ +6e-05, ~0 far inside
  solver noise).
- **D20 booked:** linear_ternary 0.01012 is SUFFICIENT —
  nonlinear_quadratic 0.01043 (+3% worse, overfits a linear generator;
  rel_gain −0.0305), identity_onehot 0.01015 (rel_gain −0.0023; sign-only
  ternary correlation already carries all identity signal that matters).
  Both reproduce to 4 decimals in this block's self-test.
- **Reproduction deltas (self-test, seed 2718, 2026-10-01):** markov1
  +4e-06, ternary +4e-06, shuffled −1e-06 vs the booked ledger (same draw
  stream, float64 ridge); oracle −0.000915 — exactly the booked cross-solver
  wobble class.
- **Harvest-completion note (booked honestly):** the first assembly of this
  block defined `COST_TOL = 1e-3` and booked it in its docstring but never
  wired it into `judge()` — the judge ran a hard `ternary <= oracle` and the
  self-test self-KILLed at cost +5.9e-05 (17x INSIDE the booked tolerance,
  pure oracle solver-wobble; every other gate green). Fixed by wiring the
  cost gate to its own booked contract; the KILL-of-record is kept here in
  words rather than hidden, per the VOID-of-record house pattern. A genuine
  ternarization cost (> 1e-3) still KILLs.

## COMPOSITION

- **Upstream — discovered edges plug in through `edge_source`:** any
  shared-key/edge-discovery lane supplies `callable(step_index) -> (src,
  tgt)`; the world then tests whether DISCOVERED relations carry the same
  ternary signal the random-pair D19 stream does. Everything else
  (generator, codec, arms, gates) is unchanged.
- **Upstream — any block that produces continuous pair states:** feed the
  two streams to `ternary_corr` to get the {-1,0,+1} percept (the codec is
  dependency-free; deadband is the only knob and is booked at 0.15).
- **Downstream — receipt wrapping:** `run_arms`' receipt dict is plain JSON
  and folds straight into a g7-watt-receipt wrapper (`g7_watt_wrapper`) /
  envelope (`envelope_guard`) — seed, arm MSEs, gates, and the booked
  reference all survive serialization; `judge()`'s verdict/reason pair is
  the gate section.
- **Downstream — judgment:** a format_first_gate-style batched judge can
  interrogate a run's receipt; this block's own judge() is the frozen
  pre-registration those questions are scored against.
- **Sibling — exact_minimax_labels** shares the {-1, 0, +1} alphabet: game
  boards ARE ternary vectors; a perception lane can round-trip continuous
  state through `ternary_corr` and score against exact minimax labels.
- Contracts the consumer must honor: never treat the continuous diff as the
  percept (oracle is a privileged reference); keep the shuffled control in
  every headline run (a leak check that costs one arm); do not compare
  oracle-arm MSEs across solvers at better than ~1e-3; honor the ≥3-seed /
  std==0→INCONCLUSIVE law on any headline claim.

## SELF-TEST

Command (from the lab root, CPU-only, ~2 s wall / ~26 s thread-time):

```
python3 blocks/ternary_transition_kernel/block.py
```

(Diagnostic detail — primary receipt, ledger deltas, ablation, cross-seed
stds — prints to **stderr**; stdout carries only the single verdict line.)

Checks, per house contracts:

1. **Primary seed 2718 at the source's exact scale** (n_agents=8,
   field_dim=32, 3200 train / 800 holdout): frozen ordering via `judge()` —
   cost within COST_TOL, signal_gain > 0, shuffled within the control band.
   Ledger deltas printed: {markov1 +4e-06, ternary +4e-06, shuffled −1e-06,
   oracle −0.000915} vs BOOKED_D19.
2. **Headline across ≥ 3 seeds** (2718/2719/2720) for all four arms +
   signal_gain + ternarization_cost; any cross-seed std == 0 is booked and
   forces INCONCLUSIVE. Measured stds (recorded): markov1 1.14e-04, ternary
   8.5e-05, oracle 8.3e-05, shuffled 1.27e-04, gain 2.9e-05, cost 2.6e-06 —
   all nonzero, verdict stands.
3. **D20 ablation on a fresh seed-2718 world**: neither nonlinear_quadratic
   (rel_gain −0.0305) nor identity_onehot (rel_gain −0.0023) improves the
   linear ternary arm by ≥ the 2% pre-registered gate — both match the
   booked D20 digits.
4. A booked `KernelError` anywhere converts to a machine-readable KILL
   verdict line, never a traceback-only exit.

Recorded output (2026-10-01, numpy float64, 2.3 s wall):

```
{"verdict": "KEEP", "reason": "ternary 0.01012 ~= oracle 0.01007 (cost +0.00006, ~0, inside COST_TOL 0.001 solver noise) < markov1 0.01786 (gain +0.00774); shuffled 0.01801 within band 0.00268 of markov1", "primary_seed": 2718, ...}
```

Expected verdict: **KEEP**, final stdout line exactly one JSON object whose
top-level `"verdict"` is `"KEEP"`, exit 0.

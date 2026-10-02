# EST-FREEZE — freezing the D2 determinacy estimator (pre-registration)

Pre-registered 2026-10-01 ~15:2x AKDT by lane **EST-FREEZE** (deepseek-v4-flash, subagent),
BEFORE any estimator is run and BEFORE any number is computed. Written in response to the
D2 v1 blocker booked in RESULTS.md (build A vs build B disagreed on H5/H6: A booked reflex
det = 1.000 / spread 0.000 / H6 range 0.715; B booked reflex det = 0.469 with spread 0.50–0.52
and H6 range 0.118 with fire-output). Frozen on write; lanes never commit — Lucineer books.

- **Parent prereg:** `proposals/runs/D2-stochastic-worlds-prereg.md` (gates H1–H6, F1–F10).
- **The blocker in one line:** `determinacy(c) = 1 − H(out|fixed in)/log|O|` is *unfrozen* —
  two implementations of the *same formula* disagree because (a) the conditioning channel φ(·)
  (which input field, what binning) and (b) the small-|O| finite-sample handling are both
  open. The measure, not the worlds, is the prerequisite.
- **Scope:** resolve the estimator only. No thesis verdict is booked here. CPU-only (no GPU,
  no guard.py, no twins re-score needed — the 6 GB card is untouched, co-tenant seat stays free).

## 0. Interface (v1 must be able to swap implementations)

One shared interface, all estimators:

```python
score(records, spec, **opts) -> float in [0,1]     # 1.0 = fully determined output
```

`records` = a list of per-tick dicts (the canonical trace record). `spec` declares:
`inp(record)->hashable` (input channel φ), `out(record)->hashable` (output symbol ψ),
`O` = **declared** output alphabet size, `rule(record)->hashable` (optional declared atom).
A v1 runner imports the module, picks one estimator by name, and gets a comparable scalar.
Estimators must be pure functions of `records` × `spec` × opts (an internal RNG seed is an
opt; see C2).

## 1. Estimators (all implementable independently)

Let `b = φ(r)`, `y = ψ(r) ∈ O`, `n_b` = bin counts, `p̂(·|b)` = empirical conditional.
Weighting scheme `w` ∈ {operational (empirical mass), uniform (equal per distinct bin),
degenerate (single modal bin)}.

- **E0 — plug-in conditional entropy (the prereg formula; the thing the two builds shared).**
  `det = clamp(1 − H_MM(Y|X)/log2|O|, 0, 1)`, `H_MM` = Miller–Madow `+(K_b−1)/(2 n_b ln2)`.
  *Stated bias @|O|=2:* plug-in H is upward-biased on sparse bins ⇒ determinacy biased LOW;
  bias is **entangled with the input binning** (this is exactly why A and B disagreed), so E0
  is not stable by construction.
- **E1 — excess mode-agreement (majority predictor).**
  `A_obs = Σ_b (n_b/n)·max_k p̂(k|b)`; `A_null` = permutation mean of `A_obs` after shuffling
  ψ across records (preserves marginals, destroys the link, S=200 deterministic-seeded perms).
  `det = clamp((A_obs − A_null)/(1 − A_null), 0, 1)`.
  *Bias @|O|=2:* raw `A_obs` is optimistic (sparse bins look pure); the permutation floor
  removes the independence-expected agreement. Deterministic function ⇒ `A_obs=1` ⇒ `det=1` exact.
- **E2 — effective-alphabet / coverage-width.**
  Per bin effective outcome count `k_b = 2^{H_nat(Y|b)} ∈ [1,|O|]` (width of the effective
  support); `det_b = (|O| − k_b)/(|O| − 1)`; `det = Σ_b w_b det_b`.
  *Bias @|O|=2:* `det_b = 2 − k_b`, a single noisy draw gives `k_b<2` ⇒ near-1 (optimistic);
  denominator `|O|−1=1` makes the binary case maximally sensitive.
- **E3 — bias-corrected normalized MI (permutation-exact).**
  `I = H(Y) − H_MM(Y|X)`; `det = clamp((I_obs − E[I_null])/(H(Y) − E[I_null]), 0, 1)`,
  `I_null` = permutation mean (same S).
  *Bias @|O|=2:* permutation-exact removal of finite-sample MI bias ⇒ mildly conservative;
  each estimator call does its own permutation null, so it is self-calibrating at |O|=2.
- **E4 — split-half predictive consistency (TV).** *(own implementation)*
  Deterministic split by **tick parity** (no RNG ⇒ seed-invariant). Per bin, Laplace-smoothed
  half-sample distributions `P_even, P_odd`; `TV_b = ½Σ_k|·|`; `det_b = 1 − TV_b/TV_max` with
  `TV_max = 1 − 1/|O|` (max TV between two distributions on O); `det = Σ_b w_b det_b`.
  *Bias @|O|=2:* sparse bins + smoothing ⇒ one half misses a symbol ⇒ TV>0 ⇒ **pessimistic**,
  the opposite sign to E1/E2 — useful bracketing.
- **E5 — per-bin purity, Wilson lower bound.** *(own implementation)*
  `det = Σ_b w_b · LB95(mode_count_b, n_b)` (Wilson score lower bound on the modal fraction).
  *Bias @|O|=2:* strictly conservative at small `n_b`; exact 1.0 on a pure bin with `n_b≥1`
  (Wilson LB of a 100% bound is 1.0).

E1/E3 share the permutation machinery; E4/E5 share nothing with E0–E3 (independent code paths).

## 2. Cross-validation protocol (identical material, frozen)

Material = `results/d2_build/mini_traces.json` and `fb_traces.json` (16 worlds real + 16
stochastic, both builds). det arm = the `real` (unmodified-path) worlds; sto arm = `sto`.

- **C1 — synthetic-atom exactness (calibrated bias vs analytic truth).** Build fully
  deterministic functions `y = atom_k(φ)` with `|O| = k` for k=2..6 on the real per-world
  sample size, PLUS a noisy family `y = correct w.p. q` (q ∈ {1.0,0.9,0.75,0.6}) whose
  analyic determinacy `1 − H(p)/log2 k` is known. Requirement: every FROZEN candidate returns
  **exactly 1.000** on the q=1.0 atoms for all k, and reports a bias table
  `est − truth` for the noisy family at |O|=2. Any nonzero atom bias ⇒ **disqualified** (this
  is the prereg's F4 made mechanical).
- **C2 — seed-invariance.** For each estimator, re-run with 5 internal seeds (perm RNG seed /
  split rotation). Spread across internal seeds must be **0.00** on the det arm. (E4 uses
  tick parity ⇒ automatic; E1/E3 permutation is seeded per call and must be reproducible.)
  Corroborating canary cited, not re-derived: `wdet_ed1_replay.log` — E-D1 seeds
  101/118/135 all emit the identical state hash `8c8a54a43f10`, so the det arm is trace-identical
  across the 3 registered seeds ⇒ score variance across those seeds is 0 by construction for any
  pure-function estimator.
- **C3 — cross-distribution spread (the H5 bar).** Per socket & estimator, spread of `score`
  across the three weightings (operational / uniform / degenerate) ≤ **0.15** at the smallest
  alphabet (|O|=2). Offenders counted; > ⅓ of sockets unstable ⇒ measure does not exist.
- **C4 — honest ordering (the H6 bar).** `reflex.orient` (predicted ~0.9; booked det 0.469)
  must exceed `memory.episodic` (predicted ~0.1; booked det 0.352) by **≥ 0.50** range, and
  reflex must score **≥ 0.80** on a frozen candidate (near-1 atom). alphabets swept 2→6 for the
  derived sockets.
- **C5 — interface identity.** All estimators resolve through the single `score()` entry point
  and return closeable [0,1] scalars on both builds' traces (→ v1 can swap).

## 3. FROZEN-V1 criterion (mechanical)

An estimator is **FROZEN-V1** iff **C1 ∧ C2 ∧ C3 ∧ C4 ∧ C5** all hold. If several pass, the
one with the smallest |bias| at |O|=2 and ≤ 0.15 spread wins; ties broken by fewest free opts.
**If NONE passes, book loudly** — it means the prereg's H5/H6 thresholds (0.15 / 0.50) need
re-derivation at small alphabets, which is itself a KEEP-grade finding and a v1 blocker.

## 4. Bias declarations (frozen before measurement)

Frozen bias signs at |O|=2: E0 low/encoding-coupled; E1 ~unbiased (permtation-corrected)
optimistic raw; E2 optimistic; E3 mildly conservative; E4 pessimistic; E5 conservative.
Any estimator whose measured |bias| at |O|=2 exceeds **0.10** is not eligible for FROZEN-V1
even if C1–C5 pass under clamping (clamping can hide bias — clamp-only passes are flagged).

## 5. Booking

`results/est_freeze/` (estimator module, cross-validation JSON, bias table) + own RESULTS.md
entry + one QUEUE.md line. **DO NOT COMMIT** (lane rule).

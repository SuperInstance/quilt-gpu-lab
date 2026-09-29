# ie1 — Reichardt correlators → 4 motion family codes (the lobula-plate rung)

**status: ready-for-dev** (written before any ie1 code exists)
**date:** 2026-09-28 (~20:45 AKDT)
**baseline_revision:** ab8ec08f0b8d919f21df452526d3578602223e3a
**science:** `docs/insect-vision-science-2026-09-28.md` §1.2 (HRC math + the four signature
properties), §1.5 (port-ready pseudocode), §2.2–2.3 (T4a-d/T5a-d = 4-cardinal arity, pooling
operator), §4 (pooling earns hyperacuity), §6 COPY list (items 1–3, 6)
**lane constraint:** CPU ONLY — K2 owns the GPU. No cuda imports, no torch, no `.gpu.lock`
writes. numpy on system python3.

---

## 1. The question (frozen)

Does the elementary motion-detector arithmetic — delay-LP → multiply → mirror-subtract on
**adjacent cell pairs**, pooled into **4 cardinal-direction family codes** (the T4a-d/T5a-d
arity, science §2.2) — carry enough directional information that a linear reader can decode
true motion direction from the code stream alone?

This is the lobula-plate rung of the insect-eye program: thousands of local correlators →
4 wide-field codes, and (science §4) the *reader* on the pooled codes is where sub-pitch
drift readout comes from — never from a single correlator.

## 2. Design (frozen)

**Correlator (science §1.5 pseudocode, signed inputs):**
- Signed contrast prefilter per frame: `c = I − mean(I)` (the cheap optional prefilter;
  not a required stage — DEPART #6).
- Delay arm: exact first-order low-pass, ZOH discrete: `lp += (1 − e^(−dt/τ))·(c − lp)`,
  dt = 1 frame. **τ = 2 frames baseline** (task spec; fly analogue 25–50 ms, science §1.3 —
  τ is a dial, swept as diagnostic, gate frozen at 2).
- Four cardinal subtypes on axis-aligned adjacent pairs (rectangular-lattice honesty,
  DEPART #2 — per-axis tuning documented, diagonals not used day-one):
  - `D_R(x) = lp[x]·c[x+d] − c[x]·lp[x+d]` (d = +x) — positive for rightward motion
  - `D_L(x) = lp[x]·c[x−d] − c[x]·lp[x−d]` (d = −x)
  - `D_U`, `D_D`: same form on the ±row axis (array rows: D_D = +row)
- **Pool:** `code[dir](t) = mean over interior cells of D_dir(x,t)` — the LP wide-field
  pooling operator (§2.3). 4 signed codes per frame = the fam code vector.
  Known consequence, documented not hidden: mirror pairs pool to exact negatives
  (`L = −R`, `D = −U`) under translation-invariant pooling — that is HS-cell-style mirror
  antagonism (science §2.2), and ridge handles the collinearity.

**Stimuli (deterministic, seeded, no GPU):** 2D cell lattice, densities **8², 16², 32²**
(Δφ = 1 cell). Two families:
- **Drifting gratings:** `I = 1.0·sin(2π(x·vx + y·vy)/λ − ωt)`, ω = 2πv/λ;
  directions {R, L, U, D}, speeds v ∈ {0.25, 0.5, 1.0} cells/frame, λ ∈ {8, 16} cells.
- **Moving blobs:** Gaussian bump σ ∈ {2, 3} cells, directions {R, L, U, D},
  v ∈ {0.25, 0.5}, path centered per sequence, per-seed jitter ≤ 1 cell.
Sequences: 60 frames, first 12 discarded (LP warmup). Per config: 4 train + 4 test
sequences, seeds = frozen formula from a base seed (20260928) + config index.

**Reader (the science-§4 readout):** ridge regression (frozen α = 10⁻², features
z-scored on train stats), features = 4 fam codes at frame t.
- **PRIMARY target (the gate):** true **direction unit vector** (vx, vy) — "decoding true
  motion direction".
- Reported secondary: **velocity** target v·(vx, vy) (the §4 continuous-drift decode) and
  cardinal-direction classification accuracy (angle snap of the decoded vector).

## 3. THE GATE (pre-registered, frozen — verdict vocabulary KEEP/KILL/INCONCLUSIVE only)

Metric: **multi-output R²** on held-out test frames, pooled over both target components:
`R² = 1 − ΣSS_res / ΣSS_tot`, at τ = 2 frames, computed independently per cell density.

- **KEEP-iff:** R²(direction) ≥ **0.5** at **≥ 2 of the 3 densities** (all three reported).
- **KILL-iff:** R²(direction) < 0.5 at 2 or more densities.
- **INCONCLUSIVE:** otherwise (report all numbers, no verdict inflation).
- **Never loosen.** Threshold and metric frozen before any ie1 code exists.

## 4. Diagnostics (reported alongside, not gated)

1. **Aliasing check (task-required):** λ sweep {1.5 … 8} cells at v = 0.5, τ = 2, 32²
   lattice, rightward grating → pooled D_R. HRC prediction: response ∝
   `c²·sin(2πΔφ/λ)·ωτ/(1+(ωτ)²)` — **sign flip at λ = 2Δφ = 2.0 cells**. Report measured
   zero-crossing (interpolated) vs predicted 2.0, and shape correlation vs the analytic
   curve (single scale factor fit).
2. **c² fingerprint** (science COPY #6 — the multiplicative-step unit test): contrast
   c ∈ {0.25, 0.5, 1.0} → measured amplitude ratios vs predicted 1 : 4 : 16.
3. **Temporal tuning:** v sweep at λ = 8, τ = 2 → measured peak v* vs predicted
   λ/(2πτ) ≈ 0.637 cells/frame (the ωτ = 1 optimum, science §1.2 property 2).
4. **τ sweep:** gate R² re-computed at τ ∈ {1, 2, 4} frames (density 16²), descriptive —
   the gate itself stays at τ = 2.

## 5. Artifacts & discipline

- Plan (this file): `proposals/runs/ie1-plan.md`.
- Code: `experiments/ie1_reichardt.py` — **numpy only**, stdlib json; `python3 -m
  py_compile` BEFORE running; system python3; no GPU/cuda/torch; nothing written outside
  `experiments/`, `results/`, `RESULTS.md`, `proposals/runs/`.
- Results: `results/ie1_reichardt.json` — every density, every τ, aliasing table,
  fingerprint table, gate arithmetic, verdict computed by the script itself. No float32
  leaks (rounded Python floats only). **No artifact = no report; no fabricated numbers.**
- Ledger: dated block appended to `RESULTS.md` with verdict + real numbers from the JSON.
- Commit: pathspec-scoped to ie1 files only (plan + code + results + RESULTS.md);
  `git push origin main`. Dirty repo state (`.gpu.lock`, training/*, stderr logs) untouched.

## 6. Predictions (written before the fire, for the record)

- Gate: PASS comfortably — the codes' sign structure is strongly direction-tuned by
  construction; expected R²(direction) > 0.8 at all three densities. The interesting
  numbers are the *diagnostics*, not the gate.
- Aliasing: measured zero-crossing within ~0.15 cells of 2.0; shape correlation > 0.98.
  For λ < 2 the sampled grating is undersampled and the correlator reports *reversed*
  motion — the diagnostic documents the fly's known alias, it is not a bug.
- c² fingerprint: measured ratios within ~20% of quadratic (LP memory makes exact c²
  hold in the time-average, not instantaneously).
- Temporal peak: within ~30% of 0.637 cells/frame.
- If the gate FAILS: the fault order to check is (1) τ vs frame-rate mismatch (correlator
  starved — science §1.5), (2) pooling sign error, (3) ON/OFF split (Eichner two-detector
  form) as the upgrade path. Not by loosening the gate.

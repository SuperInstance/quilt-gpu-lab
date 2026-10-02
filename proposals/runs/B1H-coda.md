# B1H-CODA — NAME THE HYBRID'S OWN RAMP FLOOR, AND TEST WHETHER THE @1e-3 RAMP TAIL YIELDS TO A TWO-KNOT ATOM

Lane **B1H-CODA**. The **B1-family coda**, booked at **B1G's** landing
(`results/b1g/RESULTS-ENTRY.md`; mission text 2026-10-01 18:2x AKDT). B1G
**reversed B1F**: the ramp is **epochs/loss-shaped**, not representational —
but its own mechanism section names the *dominant* lever as the **crossing
width itself** (B1F measured `hybridv2` at **w64 = 0.2930**, *below* the
crossing; `w96` clears at **40ep already 0.9562**). B1G closes with two open
questions:

1. **the hybrid's own floor** — bisect the hybrid ramp atom-gate crossing
   `{64, 80, 96}` to name the width at which the hybrid clears 0.90, to pair
   against the plain numbers (`b1e` plain w64 0.5675 / `b1f` plain w96 0.9617);
2. **the residual @1e-3 ramp tail** — `h96_mse_ep160` still leaves
   **ramp@1e-3 = 0.8247** (17.5 % of ramp samples off by >1e-3). Is that tail
   **interface-shaped** (a second break the single-knot atom cannot express — a
   two-knot atom buys it), or is it the **map's intrinsic quantization**?

Pre-registered **2026-10-01 18:3x AKDT, BEFORE FIRE** — before any trace was
regenerated, any net built, or any parameter trained. Gates frozen here; the
verdict is booked either way. Master seed **2718**. Reuse of the **B1G driver
wholesale** (`experiments/b1g_epochs_vs_ramp_loss.py` is imported; it in turn
imports the B1F driver + B1C engine UNCHANGED); B1G's safeguards kept
(prereg-arm assert + append-window guard snapshot). B1G's saved
`model_hybridv2_w96_mse_seed2718_ep160.pt` is **reused as the single-knot
arm** in Part B (resume-not-rebuild). **NO COMMIT.**

## The booked question

**Part A.** B1F's `0.2930` (hybrid ramp atom gate, w64) and B1G's `0.9562`
(w96, 40ep) sit either side of the family's 0.90 gate. Where, exactly, does the
**hybrid's own** ramp atom-gate cross 0.90? Name it — bisect at **160ep (B1G's
best recipe)**.

**Part B.** At the crossing width (96) and best recipe (MSE, 160ep) the ramp
atom gate reads **0.9979 @5e-2** but the sharp tail is **0.8247 @1e-3**. The
single-knot atom is `sign(b−p)·a·relu(u−k)` — *piecewise-linear with ONE knot*.
The law it must imitate (`b1c` engine, verbatim) is
`Δ = sign(b−p)·min(s, u−1.5)` for `u > 1.5` — a **single knot at u = 1.5**, so
the atom family *contains* the law exactly. Therefore a residual
`@1e-3` tail is either (i) **interface-shaped** — the deployed hybrid blends the
atom through **state-dependent gates** `g_dz(X), g_r(X)` and a regression head,
and a *second* knot lets the learned piece track the composition where one knot
cannot; or (ii) the **map's intrinsic quantization** — no second knot helps and
the tail is the residual floor of the whole deployed map.

**BOOKED QUESTION (verbatim):** *name the hybrid ramp atom-gate crossing width
(where ramp@5e-2 crosses 0.90), and test whether a two-knot ramp atom buys the
residual @1e-3 tail (≥ 0.05, CI excl 0) WITHOUT regressing the deadzone below
0.99.*

## Arms (frozen) — 5 preregistered arms, single seed 2718

All arms: architecture family `hybridv2` (B1F's class, reused unchanged) unless
noted; loss = **MSE** (B1G's deployed objective **verbatim**: deployed per-sample
MSE + `1.0·BCE(g_dz, deadzone-label) + 1.0·BCE(g_r, ramp-label)`); epochs **160**
(B1G's best recipe); seed **2718**.

| arm name | kind | width | epochs | note |
|---|---|---|---|---|
| `w64_mse_ep160`  | `hybridv2`    | 64 | 160 | B1F's width, carried to the best recipe |
| `w72_mse_ep160`  | `hybridv2`    | 72 | 160 | bisect |
| `w80_mse_ep160`  | `hybridv2`    | 80 | 160 | bisect |
| `w88_mse_ep160`  | `hybridv2`    | 88 | 160 | bisect |
| `w96_2knot_ep160`| `hybridv2_2k` | 96 | 160 | Part B: two-knot ramp atom |

**Reference (not counted, reused):** B1G's `h96_mse_ep160` (single-knot w96,
160ep) checkpoint — the Part B **baseline** and the width-bisection upper
reference (`ramp@5e-2 0.9979`, `ramp@1e-3 0.8247`, deadzone@5e-2 1.0000). The
plain references are carried from B1E/B1F (`b1e` plain w64 0.5675; `b1f` plain
w96 0.9617).

**Width set rationale (declared).** B1F measured w64 (0.2930, *below* crossing)
and B1G measured w96 (0.9562 at 40ep, 0.9979 at 160ep). `{64,72,80,88}` bisects
that interval, excludes the two known points, and re-measures **w64 at the best
recipe** (B1F's number was at 40ep).

## The two-knot atom (frozen design — Part B)

`HybridV2TwoKnot` **subclasses** B1F's `HybridV2MLP` and overrides **only**
`ramp_atom`; every other component (body, regression head, deadzone gate, ramp
gate, `raw` blend) is **inherited verbatim**.

```
atom_2k(u) = sign(b−p) · [ a1·relu(u − k1)  +  a2·relu(u − k2) ]
  k1 = ramp_knot                    (nn.Parameter, init 1.0)
  k2 = ramp_knot + softplus(gap)    (gap = nn.Parameter, init softplus⁻¹(1.5),
                                     so k2 init = 2.5 → k2 > k1 GUARANTEED)
  a1 = ramp_slope                   (nn.Parameter, init 1.0)
  a2 = ramp_slope2                  (nn.Parameter, init 0.0)
```

**Design points (frozen).**
- **k2 > k1 is structural** (`softplus`), not hoped for — no post-hoc swap can
  pass as a two-knot result.
- **`a2` inits at 0.0** ⇒ the arm's **first forward is bit-identical** to the
  single-knot family (the two extra parameters are appended *after* the
  inherited ones, so the shared-parameter init draws the **same** RNG stream for
  seed 2718). The **only** free variable is the second knot — a clean A/B
  against B1G's reused `h96_mse_ep160`.
- **Param budget (frozen gate).** Two-knot atom = **4 scalars** vs the
  single-knot **2**; total network **N ≈ 19,303 vs 19,301 (+0.01 %)**. The
  budget rule is on the **NETWORK**: total params must stay within **±20 %** of
  the single-knot arm (both numbers reported). Capacity is therefore held
  fixed; any tail movement is attributable to the atom's **shape**.

## Measurements per arm (checkpoint) — frozen

1. **Crossing status** — `deadzone@5e-2` and `ramp@5e-2` (whole-trace holdout,
   deployed convention `Δ_pred = clamp(p+raw,6,54) − p`).
2. **Ramp atom-gate score** — `ramp@5e-2` (the quantity the crossing is named on).
3. **Ramp sharp tail** — `ramp@1e-3` (Part B's headline; also `@1e-2`).
4. **Learned knots** — `ramp_knot` (k1), `knot2()` (k2), `ramp_slope` (a1),
   `ramp_slope2` (a2) at the checkpoint.
5. Secondary, reported not gated: `saturation`/`clamp`, the full curve 1e-6…2e-1.

**Uncertainty (frozen).** Single seed ⇒ **bootstrap over holdout samples**:
`B = 1000` percentile bootstraps (seed 2718) of the per-sample ≤-tol indicator
**within each region**; 95 % CI = [2.5, 97.5] percentiles. **Part B uses a
PAIRED bootstrap** on the ramp region: per resample, `mean(hit_2k − hit_1k)` over
the **same** resampled samples (single-knot indicators from the reused B1G
checkpoint) — the CI is on the **difference**. `std == 0` in the **deciding** boot ⇒
INCONCLUSIVE for that arm; never PASS. **Degenerate rule (precise, pre-fire
clarification):** *deciding boot* = the **Part B paired-difference** bootstrap
(zero-variance difference ⇒ INCONCLUSIVE) or a **gated region with zero holdout
support** (`n == 0` ⇒ INCONCLUSIVE). A *perfect* region score whose bootstrap CI
is pinned at `[1.0, 1.0]` is **not** degenerate — it is booked as `1.0` (B1G
precedent: `h96_mse_ep160` deadzone@5e-2 = 1.0000, CI [1.0000,1.0000], PASS).

## Gates (frozen) — mechanical, preregistered arms ONLY

- **G-B1H1 (name the hybrid floor).** A width `w ∈ {64,72,80,88}` **clears** iff
  `ramp@5e-2 ≥ 0.90` **AND** ramp bootstrap `CI_low > 0.90` **AND**
  `deadzone@5e-2 ≥ 0.90` **AND** deadzone `CI_low > 0.90` (crossing intact).
  PASS iff ≥ 1 width clears; the **named hybrid floor = min clearing width**
  (report `> 88` if none clears, plus the softer "mean ≥ 0.90" reading).
- **G-B1H2 (two knots buy the tail).** PASS iff, for `w96_2knot_ep160`,
  - paired ramp `@1e-3` gain vs the reused single-knot `h96_mse_ep160`:
    **point ≥ 0.05 AND paired-boot `CI_low > 0`** (CI excludes 0), **and**
  - **no deadzone regression**: two-knot `deadzone@5e-2 ≥ 0.99`, **and**
  - the crossing is kept: two-knot `ramp@5e-2 ≥ 0.90`.

## Verdict mapping (frozen) — the sentence booked

- **G-B1H2 PASS** → book
  **"the residual @1e-3 ramp tail was interface-shaped — two knots buy it."**
  Lane **KEEP**.
- **G-B1H2 FAIL** → book
  **"the tail is the map's intrinsic quantization — B1 closes with the tail
  booked as a limit."** Lane **KILL** (B1 family closes).
- Degenerate region support / zero-variance boot ⇒ **INCONCLUSIVE**, never PASS.

Part A is a **naming** measurement: whichever floor is named, it is booked
verbatim (the floor number is the deliverable; it does not gate the B1 close).

## Controls (frozen — must pass before any gate number is read)

Reused **verbatim** from B1G/B1F:

1. **C1 law equivalence** — switch `law` branch vs pristine `ai.track` on ≤4,000
   holdout states: **bit-identical** (`max|Δ| = 0`).
2. **C4 frame cross-check** — regenerated holdout `(X, Y, META)` from the B1C
   engine (unchanged) must equal **all four** of `results/b1c/`,
   `results/b1e/`, `results/b1b_kink_runB/`, `results/b1_distill/` holdouts with
   `max|ΔX| = max|ΔY| = max|ΔMETA| = 0`.
3. **C6 anchor reproduction** — B1D's saved width-128 linear-head anchor nets,
   re-scored; per-region @5e-2 must match B1C's **booked** `cap@ep40` within
   **|Δ| < 0.05**.
4. **C7 anchor vs B1D booked** — the same reused nets re-scored must match B1D's
   booked `anchor_cap128` cells to **|Δ| < 1e-6** (bit-exact net-reuse proof).
5. **Prereg-arm assert (B1E/B1F/B1G safeguard)** — the verdict-counted set must
   equal the **5** preregistered arm names exactly; the anchor and the reused
   single-knot reference are **never counted**.

## Budget + guard (frozen) — no receipt → run VOID

- **Wh envelope ≤ 3 Wh measured**; `Guard(task_id="B1H-coda",
  seed="2718", timeout_s=3600, receipt_dir=results/b1h/guard)`. Preflight free
  VRAM ≥ 1024 MiB, temp ≤ 80 °C. **< 1 GB free → retry once after 60 s → still
  short → NOT-RUN** (booked). G7 watt receipt (`g7-watt-receipt@1`) mandatory.
- **INSTRUMENT-01 ramp** — ≥ 0.6 s sustained synced CUDA load before the
  measured window; the ramp receipt (`ramp_s`) is written to the result.
- **Seat declared free** — no co-tenancy claim.
- **Append-window pattern:** each Guard window's `guard_summary.json` is
  snapshotted to `guard_summary.window<N>.json` immediately after receipt
  emission (B1D/B1E/B1F/B1G safeguard).

## Artifacts (frozen paths, `results/b1h/`)

`run_config.json`, `traces_meta.json`, `holdout_samples.npz`,
`model_{w64,w72,w80,w88}_mse_seed2718_ep160.pt`,
`model_w96_2knot_seed2718_ep160.pt`, `crossing.json` (Part A table — the
headline), `tail.json` (Part B paired table), `regions.json`, `controls.json`,
`result.json` (gates + booked sentence + learned knots), `RESULTS-ENTRY.md`,
`guard/` (g7 receipt + window-snapshotted summaries + ledger).
Code: `experiments/b1h_coda.py` (imports the B1G driver
`experiments/b1g_epochs_vs_ramp_loss.py` wholesale, which imports the B1F driver
and reuses the B1C engine UNCHANGED; B1D's width-128 anchor nets reused for
C6/C7; B1G's `h96_mse_ep160` checkpoint reused as the Part B single-knot arm).

B1/B1b/B1C/B1D/B1E/B1F/B1G artifacts and code are left untouched. **Do NOT
commit.**

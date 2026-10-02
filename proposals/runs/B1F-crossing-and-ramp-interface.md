# B1F — NAME THE CROSSING & IS THE RAMP AN INTERFACE PROBLEM TOO?

Lane **B1F-CROSSING-AND-RAMP-INTERFACE**. Direct follow-up to **B1E**
(`results/b1e/`, booked 2026-10-01 16:4x): *"the linear-head floor is > 64 at
40ep, bracketed (64, 128]; the width story is at the threshold, the head story
is at the margin; the ramp needs BOTH > 64 AND reweight (plain w64 ramp 0.5675,
reweight 0.7977, gate 0.90) while the deadzone clears with reweight at w48."*
Pre-registered **2026-10-01 16:5x AKDT, BEFORE fire** — before any trace was
regenerated, any net built, or any parameter trained. Gates frozen here; the
verdict is booked either way. Seed **2718**.
Reuse of B1D/B1C code, engine, frame and holdout **wholesale**; B1E's
safeguards kept (prereg-arm assert + append-window guard snapshot).
**NO COMMIT.**

## The two booked questions

**Q1 — NAME THE CROSSING.** B1E bracketed the linear-head floor as (64, 128]
via control C6 (= B1C's `cap` arm at width 128). B1F **bisects {80, 96}** under
the plain linear head (3 seeds each) and adds **`linear reweight w80`** to test
whether the region-reweight at width 80 **clears the ramp gate** (B1E: reweight
lifted w64 ramp 0.5675 → 0.7977; does the lift, plus width 80, reach ≥ 0.90?).
**Deliverable: the named crossing width** = min w ∈ {80, 96} whose **plain**
linear arm PASSes both regions; if neither passes, book **floor > 96**.

**Q2 — IS THE RAMP AN INTERFACE PROBLEM TOO?** B1D's hybrid arm showed a
**deadzone atom gate** nails the deadzone exactly (0.9998 @5e-2) even when its
regression head fails the region. B1F builds **hybrid head v2**: the same
regression body **plus atom gates for BOTH regions** — the B1D deadzone atom
gate **and a ramp atom gate** (a *ramp-shaped* output parameterization for
ramp-region items — **piecewise-linear in the cue**). Trained at **width 64**
(where plain regression FAILed and where the deadzone atom already worked),
3 seeds.
- If v2 nails **BOTH** regions at w64 where plain regression needed > 64 +
  reweight → book **"both regions are interface problems at 40ep; the capacity
  floor is an interface story."**
- If the **ramp atom gate fails too** → the ramp is **genuinely
  representational** (no interface we supply closes it at 40ep).

## Frozen architecture

Common: **body** = B1C `cap`-arm shape, **3 hidden ReLU layers** of width `w`;
deployed action convention verbatim `Δ_pred = clamp(p + raw, 6, 54) − p`; Adam
lr 1e-3, batch 4096, CUDA, seeds 2718/2719/2720, **40ep ONLY**.

- **`linear`** — LINEAR / identity head, `raw = z_out` (B1C `cap` head; B1E's
  class, reused unchanged).
- **`hybridv2`** — same body + three heads:
  - **regression** head `reg = 1.05 · tanh(z_reg)` (B1D hybrid's regression head);
  - **deadzone atom gate** `g_dz = σ(z_dz)` (B1D hybrid's gate, verbatim);
  - **ramp atom gate** `g_r = σ(z_r)`, and a **ramp atom**
    `ramp_atom = sign(b−p) · a · relu(u − k)` where `u = |b−p|` is the cue and
    `(a, k)` are **learnable scalars** (a piecewise-linear-in-cue ramp shape).
  - composition: `raw = (1 − g_dz) · [ (1 − g_r) · reg + g_r · ramp_atom ]`.
  - loss: deployed MSE `+ 1.0·BCE(g_dz, deadzone-label) + 1.0·BCE(g_r, ramp-label)`
    (region labels on the **train** split, from law ground truth).
  - **Interface-honesty note (frozen):** the ramp atom supplies the **shape
    family** only (piecewise-linear in the cue, single knot); the constants
    `(a, k)` are **learned from data**, not supplied. A PASS therefore books
    *"the ramp's piecewise-linear shape family resolved it"* — a statement about
    the interface, not about a hard-coded law.

## Arms (frozen) — 4 arms × 3 seeds = 12 nets, 40ep only

| arm name | kind | width | weighting | role |
|---|---|---|---|---|
| `linear_plain_w80` | linear | 80 | plain | Q1 bisect |
| `linear_plain_w96` | linear | 96 | plain | Q1 bisect |
| `linear_reweight_w80` | linear | 80 | reweight | Q1 reweight@80 |
| `hybridv2_w64` | hybridv2 | 64 | plain (+gates) | Q2 interface probe |

`reweight` = B1C's region-reweight mechanism **verbatim** (inverse train-split law
region frequency, mean 1, clip [0.5,30]).

## Primary gate (frozen) — per-region, absolute

Per arm, mean over **3 seeds**, held-out whole traces:

- **PASS** iff `deadzone@5e-2 ≥ 0.90` **AND** `ramp@5e-2 ≥ 0.90` **AND both stds
  > 0**. `std == 0 → INCONCLUSIVE`, never PASS.
- Secondary, **reported not gated**: @1e-2 (and @1e-3); `saturation`/`clamp`;
  the aggregate; the full curve 1e-6…2e-1.
- **Named crossing width** = min w ∈ {80, 96} with `linear_plain_w{w}` PASS;
  else **> 96**.
- **reweight@80 verdict** = does `linear_reweight_w80` PASS (and specifically its
  ramp@5e-2 ≥ 0.90)?
- **Ramp-only table (frozen headline)** = `ramp@5e-2` / `ramp@1e-2` (mean ± std)
  for all four arms.
- **Interface verdict (Q2, mechanical)** — from `hybridv2_w64`:
  - deadzone PASS **and** ramp PASS → **"INTERFACE: both regions are interface
    problems at 40ep; the capacity floor is an interface story."**
  - deadzone PASS **and** ramp FAIL → **"REPRESENTATIONAL: the ramp resists the
    ramp atom gate; the ramp is genuinely representational."**
  - deadzone FAIL → **"INCONCLUSIVE for the interface reading"** (report cells).

## Controls (frozen — must pass before any gate number is read)

1. **C1 law equivalence** — switch `law` branch vs pristine `ai.track` on ≤4,000
   holdout states: **bit-identical** (`max|Δ| = 0`).
2. **C4 frame cross-check** — regenerated holdout `(X, Y, META)` from the **B1C
   engine** (`b1c_value_fidelity_engine.mjs`, unchanged) must equal **all three**
   of `results/b1c/`, `results/b1b_kink_runB/`, `results/b1_distill/` holdouts
   with `max|ΔX| = max|ΔY| = max|ΔMETA| = 0`.
3. **C6 anchor reproduction** — reuse **B1D's saved width-128 linear-head anchor
   nets** (`results/b1d/model_anchor_cap128_seed*_ep40.pt`), re-score; per-region
   @5e-2 must match B1C's **booked** `cap@ep40` (0.9957 / 0.9186) within
   **|Δ| < 0.05**. Cross-lane tie + reuse proof. **NOT an arm.**
4. **C7 anchor vs B1D booked** — the same reused nets re-scored must match B1D's
   booked `anchor_cap128` cells to **|Δ| < 1e-6** (same nets, same frame).
5. **Prereg-arm assert (B1E safeguard)** — the verdict-counted set must equal the
   4 preregistered arm names exactly; the anchor is never counted.

## Verdict mapping (mechanical) — preregistered arms ONLY

- ≥1 arm PASS → lane **KEEP**; name the crossing width, the reweight@80 verdict,
  and the interface verdict.
- No PASS but ≥1 reweight lift → **PARTIAL** (report the crossing as > 96).
- No PASS and no lift → **KILL** (floor > 96, ramp sticky).
- Any arm `std == 0` on a gated region → **INCONCLUSIVE** for that arm.

## Budget + guard (frozen) — no receipt → run VOID

- **Wh envelope ≤ 6 Wh measured** (12 tiny nets; B1E: 24 nets = 4.91 Wh).
- `Guard(task_id="B1F-crossing-and-ramp-interface", seed="2718",
  receipt_dir=results/b1f/guard)`. Preflight free VRAM ≥ 1024 MiB, temp ≤ 80 °C.
  **< 1 GB free → retry once after 60 s → still short → NOT-RUN** (booked). G7
  watt receipt (`g7-watt-receipt@1`).
- **Co-tenancy declared:** the 7B ollama seat + the pong grind hold the card.
- **Append-window pattern:** each Guard window's `guard_summary.json` is
  snapshotted to `guard_summary.window<N>.json` immediately after receipt
  emission (B1D/B1E safeguard).

## Artifacts (frozen paths, `results/b1f/`)

`run_config.json`, `traces_meta.json`, `holdout_samples.npz`,
`model_{linear_plain_w80,linear_plain_w96,linear_reweight_w80,hybridv2_w64}_seed{2718,2719,2720}_ep40.pt`,
`regions.json` (per-region table — the headline), `ramp_only.json`,
`agreement.json` (full curve), `controls.json` (C1/C4/C6/C7),
`result.json` (verdict + crossing + interface verdict), `RESULTS-ENTRY.md`,
`guard/` (g7 receipt + window-snapshotted summaries + ledger).
Code: `experiments/b1f_crossing_ramp_interface.py` (imports the B1D/B1C drivers
for frame/gen/regions/helpers; reuses `experiments/b1c_value_fidelity_engine.mjs`
**unchanged**).

B1/B1b/B1C/B1D/B1E artifacts and code are left untouched. **Do NOT commit.**

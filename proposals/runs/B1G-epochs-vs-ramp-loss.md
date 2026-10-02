# B1G — IS THE 40ep RAMP NUMBER AN EPOCHS ARTIFACT OR A LOSS-SHAPE ARTIFACT?

Lane **B1G-EPOCHS-VS-RAMP-LOSS**. The **B1-family closer**, booked at B1F's
landing (see QUEUE/ROADMAP; mission text 2026-10-01 17:34 AKDT). Direct
follow-up to **B1F** (`results/b1f/`, booked 17:0x): *"the linear-head crossing
is 96 plain / 80 reweight; the ramp is REPRESENTATIONAL at 40ep — hybrid-v2's
ramp atom gate FAILS 0.2930 at w64, WORSE than plain regression 0.5675 (learned
k 1.35–1.42 vs law 1.5; the deadzone gate bleeds across u≈1.5)."* B1E showed the
ramp needs **width > 64 AND reweight** (0.5675 / 0.7977 at w64).

Pre-registered **2026-10-01 17:3x AKDT, BEFORE FIRE** — before any trace was
regenerated, any net built, or any parameter trained. Gates frozen here; the
verdict is booked either way. Master seed **2718**.
Reuse of the B1F driver / B1C engine / frame / holdout **wholesale**
(`experiments/b1f_crossing_ramp_interface.py` is imported; the B1C engine
`experiments/b1c_value_fidelity_engine.mjs` is reused UNCHANGED); B1F's
safeguards kept (prereg-arm assert + append-window guard snapshot).
**NO COMMIT.**

## The booked question

B1F closed the B1 family attribution as *"deadzone = interface problem, ramp =
representational"* — but that call rests entirely on **hybrid-v2 at width 64,
40 epochs, plain MSE**. Two confounds are untested:

- **EPOCHS** — is 0.2930 simply undertrained? (B1F's own note flags the 300ep
  regime as degenerately `std == 0`; the budget, not the interface, may be the
  wall.)
- **LOSS SHAPE** — a ramp-specific *objective* (not a ramp-shaped *head*) was
  never supplied. B1F handed the interface the ramp's **shape family**; it never
  asked the loss to care about the ramp **band**.

**BOOKED QUESTION (verbatim):** does longer training **or** a ramp-weighted
objective close the ramp gap **WITHOUT** breaking the crossing?

The test is run at **width 96 — the plain crossing point named by B1F** — so
that capacity is *not* the free variable and any ramp movement is attributable
to epochs or loss shape alone.

## Arms (frozen) — 2 losses × 3 epoch milestones = 6 arms, width 96, seed 2718

Architecture **`hybridv2`** (B1F's class, **reused unchanged**): regression body
(3 hidden ReLU layers of width 96) + regression head `1.05·tanh(z_reg)` +
**deadzone atom gate** `g_dz = σ(z_dz)` + **ramp atom gate** `g_r = σ(z_r)` and
ramp atom `sign(b−p)·a·relu(u−k)`, `u = |b−p|`, `(a, k)` **learnable**;
`raw = (1−g_dz)·[(1−g_r)·reg + g_r·ramp_atom]`.

| arm name | loss | width | epoch milestone | note |
|---|---|---|---|---|
| `h96_mse_ep40`   | MSE | 96 | 40  | b1f-machinery reference carried to the crossing width |
| `h96_mse_ep80`   | MSE | 96 | 80  | epochs lever |
| `h96_mse_ep160`  | MSE | 96 | 160 | epochs lever (deepest) |
| `h96_rw_ep40`    | ramp-weighted | 96 | 40  | loss-shape lever at the booked epoch |
| `h96_rw_ep80`    | ramp-weighted | 96 | 80  | both levers |
| `h96_rw_ep160`   | ramp-weighted | 96 | 160 | both levers (deepest) |

**Losses (frozen).**
- **MSE** = B1F's deployed objective **verbatim**: per-sample deployed MSE
  `mean((clamp(p+raw,6,54)−p − Y)²)` **plus** `1.0·BCE(g_dz, deadzone-label) +
  1.0·BCE(g_r, ramp-label)` (region labels on the **train** split, from law
  ground truth).
- **ramp-weighted** = the same objective with the **deployed-MSE term** weighted
  per sample by `w_i = 1 + RAMP_BOOST · 1[i ∈ ramp]`, `RAMP_BOOST = 10.0`
  (frozen; weights NOT renormalised — the BCE gate terms stay unweighted).
  A single-purpose objective that concentrates on the ramp band
  (train ramp fraction ≈ 3.7 % ⇒ ramp carries ≈ 30 % of the weighted MSE mass).
  Not B1C's inverse-region-frequency reweight: this weights the **ramp band
  alone**.

**Nested trajectory (frozen).** Each loss is trained **once to 160 epochs** on a
single seed; state dicts are **snapshotted at epochs {40, 80, 160}** and each
snapshot is a **first-class arm** scored independently. This yields a true
ramp-vs-epochs trajectory within a loss and keeps the arm matrix
{loss} × {40, 80, 160} exact.

## Measurements per arm (checkpoint) — frozen

1. **Crossing status** — the B1F gates at w96: `deadzone@5e-2` and `ramp@5e-2`
   (whole-trace holdout, deployed convention). PASS = both ≥ 0.90.
2. **Ramp atom-gate score** — `ramp@5e-2` for the hybrid arm (the quantity B1F
   read as 0.2930 at w64).
3. **Learned-k** — `ramp_knot` (and `ramp_slope`) at the checkpoint.
4. Secondary, reported not gated: `ramp@1e-2`, `ramp@1e-3`, `deadzone@1e-2`,
   `saturation`/`clamp`, the full curve 1e-6…2e-1.

**Uncertainty (frozen).** Single seed ⇒ **bootstrap over holdout samples**:
`B = 1000` percentile bootstraps (seed 2718) of the per-sample ≤-tol indicator
**within each region**; 95 % CI = [2.5, 97.5] percentiles.

## Gates (frozen) — mechanical, preregistered arms ONLY

- **G-B1G1 (the ramp moves).** PASS iff **∃ preregistered arm** with
  `ramp@5e-2 ≥ 0.80` **AND** bootstrap **95 % CI lower bound > 0.5175**
  (= the plain-40ep reference 0.5675 − 0.05).
- **G-B1G2 (no crossing trade-off).** PASS iff **∃ arm satisfying G-B1G1** that
  **also** keeps the crossing intact at w96: `deadzone@5e-2 ≥ 0.90` **AND**
  bootstrap **95 % CI lower bound > 0.90**.

## Verdict mapping (frozen) — the sentence booked

- **G-B1G1 PASS ∧ G-B1G2 PASS** → book
  **"the ramp is epochs/loss-shaped after all — B1F's representational call was
  undertrained."**
- **G-B1G1 FAIL across all preregistered arms** → book
  **"the ramp floor is stable — representation limit confirmed at the margin"**
  (this closes the B1 family for good).
- **G-B1G1 PASS ∧ G-B1G2 FAIL** → book the trade-off explicitly:
  **"the ramp can be bought, but only by breaking the interface (the crossing)."**
- Any arm with degenerate region support ⇒ INCONCLUSIVE for that arm; never PASS.

## Controls (frozen — must pass before any gate number is read)

Reused **verbatim** from B1F (`experiments/b1f_crossing_ramp_interface.py`):

1. **C1 law equivalence** — switch `law` branch vs pristine `ai.track` on ≤4,000
   holdout states: **bit-identical** (`max|Δ| = 0`).
2. **C4 frame cross-check** — regenerated holdout `(X, Y, META)` from the B1C
   engine (unchanged) must equal **all four** of `results/b1c/`,
   `results/b1e/`, `results/b1b_kink_runB/`, `results/b1_distill/` holdouts with
   `max|ΔX| = max|ΔY| = max|ΔMETA| = 0`.
3. **C6 anchor reproduction** — B1D's saved width-128 linear-head anchor nets,
   re-scored; per-region @5e-2 must match B1C's **booked** `cap@ep40`
   (0.9957 / 0.9186) within **|Δ| < 0.05**.
4. **C7 anchor vs B1D booked** — the same reused nets re-scored must match B1D's
   booked `anchor_cap128` cells to **|Δ| < 1e-6** (bit-exact net-reuse proof).
5. **Prereg-arm assert (B1E/B1F safeguard)** — the verdict-counted set must equal
   the 6 preregistered arm names exactly; the anchor is never counted.

## Budget + guard (frozen) — no receipt → run VOID

- **Wh envelope ≤ 6 Wh measured**; `Guard(task_id="B1G-epochs-vs-ramp-loss",
  seed="2718", timeout_s=3600, receipt_dir=results/b1g/guard)`. Preflight free
  VRAM ≥ 1024 MiB, temp ≤ 80 °C. **< 1 GB free → retry once after 60 s → still
  short → NOT-RUN** (booked). G7 watt receipt (`g7-watt-receipt@1`) mandatory.
- **Seat declared free** (pong grind done; 7B evicted) — no co-tenancy claim.
- **Append-window pattern:** each Guard window's `guard_summary.json` is
  snapshotted to `guard_summary.window<N>.json` immediately after receipt
  emission (B1D/B1E/B1F safeguard).

## Artifacts (frozen paths, `results/b1g/`)

`run_config.json`, `traces_meta.json`, `holdout_samples.npz`,
`model_hybridv2_w96_{mse,rw}_seed2718_ep{40,80,160}.pt` (6 checkpoints),
`regions.json` (per-arm table — the headline), `ramp_only.json` (ramp trajectory),
`agreement.json` (full curve), `controls.json` (C1/C4/C6/C7),
`result.json` (gates + booked sentence + learned-k trajectory), `RESULTS-ENTRY.md`,
`guard/` (g7 receipt + window-snapshotted summaries + ledger).
Code: `experiments/b1g_epochs_vs_ramp_loss.py` (imports
`experiments/b1f_crossing_ramp_interface.py` wholesale; reuses
`experiments/b1c_value_fidelity_engine.mjs` **unchanged**; B1D's saved width-128
anchor nets reused for C6/C7).

B1/B1b/B1C/B1D/B1E/B1F artifacts and code are left untouched. **Do NOT commit.**

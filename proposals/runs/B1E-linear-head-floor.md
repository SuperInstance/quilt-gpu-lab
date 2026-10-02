# B1E — LINEAR-HEAD FLOOR: the capacity floor of the ACTUAL B1C recipe

Lane **B1E-LINEAR-HEAD-FLOOR**. Direct follow-up to **B1D**
(`results/b1d/`, commit `475c829`), which booked *"the capacity floor is > 64
at 40ep under the frozen **tanh** head"* and named the open question:
*is B1C's PASS a width story or a head story?* Pre-registered **2026-10-01
16:4x AKDT, BEFORE fire** — before any trace was regenerated, any net built, or
any parameter trained. Gates frozen here; the verdict is booked either way.
Seed **2718**. Reuse of B1D/B1C code, engine, frame and holdout **wholesale**.
**NO COMMIT.**

## The open question (handed to us by B1D)

B1D swept the **tanh** head over widths {24,32,48,64} and found no arm clears
both per-region gates — but B1D's own booked risk is that the brief pinned the
**tanh** head, while **B1C's `cap` arm** (the B1 family's only PASS; 40ep,
deadzone 0.9957 / ramp 0.9186) used a **LINEAR (identity) head** at width 128.
B1D's control **C6** reproduced that linear width-128 cap arm to `max|Δ|=4.7e-05`
and thereby **bracketed the linear-head floor as (64,128]**. B1E fills the
bracket: the **actual** capacity floor of the B1C recipe.

**Is B1C's PASS a capacity story (width) or an interface story (head)?**

## Architecture (frozen) — B1C cap-arm body + LINEAR (identity) head

- **body** = the B1C `cap` arm's shape: **3 hidden ReLU layers**, each of width
  `w` (B1C used 128×128×128; B1E sweeps `w`).
- **head** = **LINEAR / identity** — `raw = z_out`, exactly B1C's `cap` arm head
  (no tanh, no binning, no gate). This is the whole point: the *actual* B1C
  head, so the sweep measures capacity **without** the tanh interface penalty
  B1D booked.
- **deployed action** = B1/B1b/B1C's convention verbatim:
  `Δ_pred = clamp(p + raw, 6, 54) − p`. MSE on `Δ_pred` (deployed MSE).
- Adam lr 1e-3, batch 4096, CUDA, 3 seeds 2718/2719/2720, **40ep only**.

## The sweep (frozen) — 40ep ONLY

Budget **40 epochs only** (B1C/B1D both booked the 300ep regime as structurally
`std == 0` → INCONCLUSIVE; a 300ep sweep cannot resolve a floor). 40ep is also
the exact budget at which B1C's `cap` PASSED.

| axis | values | count |
|---|---|---|
| body width `w` | 24, 32, 48, 64 | 4 |
| weighting | `plain`, `reweight` | 2 |
| seeds | 2718, 2719, 2720 | 3 |

**24 nets**, all **linear-head**, depth-3 ReLU body, 40ep.

- **`plain`** — unweighted deployed MSE (B1C's `cap` weighting).
- **`reweight`** — the **B1C `reweight` mechanism verbatim**: per-tick weights =
  inverse frequency of the tick's ground-truth law region (regions on the *train*
  split), normalised to mean 1, clipped [0.5, 30], applied to deployed-MSE. No
  new degree of freedom. The brief calls this "+deadzone-reweight"; it is read as
  B1C's region-reweight (deadzone prime target, ramp also upweighted).

## Head-vs-head table (frozen) — NO retraining

The within-lane **head-vs-head** comparison reuses B1D's booked **tanh** cells
(no retraining, no GPU): at width 64, `literal B1E linear w64` vs `B1D plain_w64
tanh` and `B1D reweight_w64 tanh`. B1D numbers are read from
`results/b1d/regions.json`.

## Controls (frozen — must pass before any gate number is read)

1. **C1 law equivalence** — switch `law` branch vs pristine `ai.track` on ≤4,000
   holdout states: **bit-identical** (`max|Δ| = 0`).
2. **C4 frame cross-check** — regenerated holdout `(X, Y, META)` from the **B1C
   engine** (`b1c_value_fidelity_engine.mjs`, unchanged) must equal **all three**
   of `results/b1c/`, `results/b1b_kink_runB/`, `results/b1_distill/` holdouts
   with `max|ΔX| = max|ΔY| = max|ΔMETA| = 0`.
3. **C6 anchor reproduction (cross-lane)** — the width-128, depth-3, **LINEAR**
   head, plain body **= B1C's `cap` arm by construction**. B1E **reuses B1D's
   saved anchor nets** (`results/b1d/model_anchor_cap128_seed*_ep40.pt`, trained
   on the bit-identical frame) and re-scores them; their per-region @5e-2 means
   must match B1C's **booked** `cap@ep40` (0.9957 / 0.9186) within **|Δ| < 0.05**
   on every gated region, AND match B1D's booked `anchor_cap128` cells. This is
   the cross-lane tie and the reuse proof. **C6 is a control, NOT an arm.**
4. *(No C2 JS↔torch port: h2h is out of scope, as for B1C/B1D.)*

## Primary gate (frozen) — per-region, absolute

Per arm = (weighting, width), mean over **3 seeds**, held-out whole traces:

- **PASS** iff `deadzone@5e-2 ≥ 0.90` **AND** `ramp@5e-2 ≥ 0.90` **AND both
  stds > 0**. `std == 0 → INCONCLUSIVE`, never PASS.
- Secondary, **reported not gated**: the same table @1e-2 and @1e-3;
  `saturation`/`clamp` (rot watch: any arm whose saturation < 0.90 @5e-2 is
  booked as a trade); the aggregate; the full curve at 1e-6…2e-1.
- **The capacity floor** = the **minimum width** w ∈ {24,32,48,64} whose arm
  clears both regions — reported **separately for `plain` and `reweight`**.
- **Ramp-only finding (frozen secondary):** report `ramp@5e-2` for each arm
  separately — does the ramp close with **capacity alone** (linear head, plain)
  or does it need the **region-reweight**? (B1D: ramp was the binding region
  under every tanh knob.)
- **Mechanism bar (secondary, ≤ PASS)**: `reweight` at width w is a *mechanism
  win* over `plain` at the same w iff it beats it by **≥ +0.15 deadzone AND
  ≥ +0.20 ramp**.

## Verdict mapping (mechanical) — sweep arms ONLY

**Verdict selection counts ONLY the preregistered sweep arms** (the 8 `linear`
arms `{plain,reweight}×{24,32,48,64}`); the control `anchor_cap128` is **never**
counted (B1D's caught wart). The code asserts the counted set == those 8 names.

- ≥1 sweep arm PASS → lane **KEEP**; name the plain floor and the reweight floor.
  If the floor ≤ 64: book **"the deficit was the head/interface, not capacity"**.
- No PASS but ≥1 mechanism win → lane **PARTIAL**: reweighting moves the regions
  but does not lower the floor below max width.
- No PASS and no mechanism win → lane **KILL**: book **"capacity floor > 64 even
  with the linear head"** (and report whether ramp specifically stays short).
- Any arm with `std == 0` on a gated region → **INCONCLUSIVE** for that arm.

## Budget + guard (frozen) — no receipt → run VOID

- **Wh envelope ≤ 6 Wh measured** (24 tiny nets, 122 MB peak known from B1D).
- `Guard(task_id="B1E-linear-head-floor", seed="2718",
  receipt_dir=results/b1e/guard)`. Preflight: free VRAM ≥ 1024 MiB, temp ≤ 80 °C.
  **< 1 GB free → retry once after 60 s → still short → NOT-RUN** (booked). G7
  watt receipt (`g7-watt-receipt@1`, validator `../fleet-seeds/scripts/g7_validate.mjs`).
- **Co-tenancy declared:** the 7B ollama seat + the pong grind hold the card.
- **Append-window pattern (B1D wart fix):** each Guard window's
  `guard_summary.json` is **snapshotted** to `guard_summary.window<N>.json`
  immediately after receipt emission, so a later `--resume` window can never
  overwrite the fire window's summary (B1D's binding-digest loss).

## Artifacts (frozen paths, `results/b1e/`)

`run_config.json`, `traces_meta.json`, `holdout_samples.npz`,
`model_{plain,reweight}_w{24,32,48,64}_seed{2718,2719,2720}_ep40.pt`,
`regions.json` (per-region table — the headline), `head_vs_head.json`,
`agreement.json` (full curve), `controls.json` (C1/C4/C6), `result.json`
(verdict + floor), `RESULTS-ENTRY.md`, `guard/` (g7 receipt + window-snapshotted
summaries + ledger). Code: `experiments/b1e_linear_head_floor.py` (imports the
B1C driver for frame/gen/regions + the B1D driver for shared helpers; reuses
`experiments/b1c_value_fidelity_engine.mjs` **unchanged**).

B1/B1b/B1C/B1D artifacts and code are left untouched. **Do NOT commit.**

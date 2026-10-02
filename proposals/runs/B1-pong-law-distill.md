# B1 — Policy distillation of the pong derived law

Lane **B1-DISTILL**. Harvest of `fleet-triage/docs/RTX4050-WORKLIST.md` item B1.
Pre-registered **2026-10-01 ~14:20 AKDT, BEFORE fire** (before any trace was
generated or any parameter trained). Frozen gates; the verdict is booked either
way (results/b1_distill/ + RESULTS.md + QUEUE.md). Seed **2718**.

## Claim

A tiny MLP (<1M params) distilled from exact traces of the pong **derived law**
reaches **near-100% per-tick action agreement** with the law on held-out traces
and is **h2h-indistinguishable** from the law itself. The honest gap is the
receipt either way: if agreement stalls below the bar, or the distilled policy
loses/beats the law measurably, that number is the finding and is booked as such.

## The teacher (frozen identity)

The **shipped `quilt-arcade` pong derived law**: `games/pong/sheet.mjs`, cell
`ai.track` (const `TRACK`). It reads `paddle.<side>` (`p`) and `ball.y` (`b`) and
writes the paddle's new position. As a per-tick **action** `Δ`:

```
s      = 0.85 (left) | 0.70 (right)              # side-specific reflex speed
Δ0     = |b−p| > 1.5 ? sign(b−p)·min(s, |b−p|−1.5) : 0     # deadzone 1.5
y'     = clamp(p + Δ0, 6, 54)                    # paddle half-height clamp
ACTION = Δ = y' − p
```

**Labels are produced by EXECUTING the unmodified shipped cell under the
quilt-arcade engine** (Node child, list-form subprocess; the engine is fed a
state, `ai.track` is called, the resulting `paddle.<side>` is read back). The
law is **never reimplemented in Python** for labels. A pristine-sheet
`ai.track` is the only label source.

## Frozen trace-generation frame — **uniform-random reachable states**

Two frames were on the table: (A) states visited under **law self-play**, (B)
states reached under **uniform-random play**. **FROZEN CHOICE: (B)
uniform-random reachable states.**

Justification (two lines): the derived law is a memoryless map on
(own-paddle.y, ball.y); law self-play concentrates on the narrow correlated
slice its own competent tracking creates and under-samples the deadzone
interiors, the saturation plateaus and the clamp corners where a distilled
policy would silently diverge. Uniform-random reachable play visits the law's
full reachable operating envelope, so the agreement receipt measures the law
map rather than the sampler's competence — and the h2h receipt (below) supplies
the deployment-distribution half that (A) would have covered.

**Concretely (frozen):** traces are whole engine matches driven with both
paddles under a **uniform-random discrete policy** (each side's move drawn
uniformly from {−1, 0, +1}, seeded per trace), length **1200 ticks**, seed
`900000+i` for trace `i`. **240 traces** are generated; the split is held out
**by whole trace**: traces with `i % 5 == 0` → **holdout (48 traces)**, the
rest → **train (192 traces)**. Each tick contributes **2 samples** (left and
right), so ≈ 460k train / ≈ 115k holdout law actions. `match.step` is the only
per-tick call; states are the pre-track state of each tick (identical paddle
inputs for both sides, single `ball.y`).

## Model (frozen)

MLP `3 → 64 → 64 → 1`, `tanh` hidden, linear head, **4,481 params** (<1M).

- inputs (frozen normalization): `[(p−30)/30, (b−30)/30, side]`, side = 0 for
  left / 1 for right.
- output: `Δ_pred` (field units), **unclamped** — the action is the net's raw
  output; only the game's own position clamp (`[6,54]`) applies when the net
  drives a paddle in play.
- loss MSE on `Δ_law`; Adam lr 1e-3; 40 epochs; batch 4096; torch 2.14
  (cu126), **CUDA**, device string recorded with every number.
- **3 training seeds: 2718, 2719, 2720** (controls torch init + minibatch
  order). Everything else identical.

## Gate A — per-tick action agreement (held-out traces)

For each trained net, on the **held-out (whole) traces** only, restricted to
ticks before that trace's match closed:

- **Primary agreement** = fraction of held-out ticks with
  `|Δ_pred − Δ_law| ≤ 1e-3` (field units; 1e-3 ≈ 0.15% of a typical 0.7-step).
- secondary, reported not gated: strict `≤1e-6`; **letter agreement** (sign
  class under the same 1.5 deadzone: S/U/D); mean & max `|Δ_pred − Δ_law|`;
  max `|Δ_pred|` (budget honesty).

**Frozen gate:** mean over the 3 seeds **≥ 0.99** AND **std > 0** → **PASS**.
`std == 0 → INCONCLUSIVE` (never PASS). mean < 0.99 → **FAIL** (the gap is the
receipt). Agreement is reported to 1e-6 resolution.

## Gate B — h2h win-rate of the distilled policy vs the law itself

**Frozen seeds:** `S = {2718..2817}` (100 seeds). Per training seed, per seed
in `S`, **two** matches with sides swapped:

1. `left = distilled`, `right = law`
2. `left = law`, `right = distilled`

Both sides are clamped to the same paddle box; the distilled side applies its
predicted `Δ_pred`, the law side its exact `Δ0`. **Win = first to 7 points.**
h2h win-rate = (distilled wins) / (2·100) per training seed; booked as
**mean±std over the 3 training seeds**.

- **Control (fired first, different path):** the identical protocol with the
  law on **both** sides → aggregated win-rate for "left" must be ≈ 0.50 (its
  exactness is fixed by the swap construction). The distilled numbers are read
  only if the control lands at 0.50.
- Matches not closed within `MAX_TICKS = 20000` are **draws**, excluded from the
  win-rate and booked as a count.
- **Frozen gate:** mean ∈ [0.40, 0.60] AND std > 0 → **PASS**
  (indistinguishable). `std == 0 → INCONCLUSIVE`. Outside [0.40, 0.60] →
  **FAIL**, direction booked.

## Verdict mapping (mechanical)

- A PASS + B PASS → **KEEP** (near-100% agreement, h2h-indistinguishable).
- one PASS + one FAIL/INCONCLUSIVE → **PARTIAL** (name the failing receipt).
- A FAIL → **KILL** as stated; the measured agreement gap is the finding.
- any `std == 0` on the gated quantity → **INCONCLUSIVE** for that gate.

## Harness controls (worklist §0 compliance)

1. **Pristine-vs-switch law equivalence.** The playing harness substitutes
   `ai.track` with a mode switch whose `law` branch is character-for-character
   the shipped `TRACK` body. Before any measured number: the switch's law branch
   and the **pristine unmodified sheet's** `ai.track` are compared on the
   holdout states; **bit-identical** required (this is what lets the switch
   sheet be trusted for h2h).
2. **CPU/JS net port.** The distilled net is evaluated in JS for full-speed
   h2h; the JS forward is compared against the **torch** forward on 50k holdout
   states — `max|Δ_js − Δ_torch| < 1e-6` required, else h2h is VOID.
3. **Augmentation/rollout provenance.** Every sampled state is emitted by the
   engine (no Python physics).

## Guard + receipt (G7) — no receipt → run VOID

`Guard(task_id="B1-pong-law-distill", seed="2718", receipt_dir=
results/b1_distill/guard)`. Preflight: free VRAM ≥ 1024 MiB, temp ≤ 80 °C.
G7 watt receipt (`g7-watt-receipt@1`, validator
`../fleet-seeds/scripts/g7_validate.mjs`) sealed over the whole measured window.
**Device VRAM **< 1.5 GB** (frozen ceiling). **Co-tenancy:** a 7B ollama seat
(qwen2.5:7b Q4_K_M, ~4.18 GiB resident) may hold the card; the distilled net is
tiny and runs beside it. If Guard preflight shows **< 1024 MiB free**, retry
**once after 60 s**; still short → book **NOT-RUN**, honestly.

## Artifacts (frozen paths)

- `results/b1_distill/traces_meta.json` — frame, seeds, split, provenance.
- `results/b1_distill/holdout_samples.npz` — held-out states + law labels.
- `results/b1_distill/model_seed{2718,2719,2720}.pt` — the 3 nets.
- `results/b1_distill/agreement.json` — Gate A (+ secondary metrics).
- `results/b1_distill/h2h.json` — Gate B (+ control + draws).
- `results/b1_distill/controls.json` — equivalence + JS/torch port checks.
- `results/b1_distill/result.json` — the combined verdict.
- `results/b1_distill/guard/` — g7 receipt + guard_summary + ledger.

Code: `experiments/b1_pong_law_engine.mjs` (engine harness),
`experiments/b1_distill.py` (driver, guard, training, both receipts).
**Do NOT commit** — the keeper commits.

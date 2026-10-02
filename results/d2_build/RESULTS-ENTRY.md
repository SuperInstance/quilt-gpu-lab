# RESULTS ENTRY — D2-FIRST-BUILD (the D2 stochastic-worlds WIRING receipt)

- **lane:** D2-FIRST-BUILD · prereg `proposals/runs/D2-stochastic-worlds-prereg.md` §6 (frozen; lane D2-DESIGN)
- **date:** 2026-10-01 ~15:0x AKDT · **seed root:** 2718 · **device:** RTX 4050 Laptop 6 GB (WSL2)
- **repo pin:** `SuperInstance/quilt-dba` @ `5bbd99c99ab885fd8009655ddfbd5a3a58742364` (HEAD verified = pin)
- **scope:** wiring gates ONLY — NOT the v1 200-world thesis run. Mini books **H4 + F-gates** (§6.5).
- **files:** `results/d2_build/` — `mini_world_report.json`, `mini_traces.json`, `mini_twins.json`,
  `d2_stochastic_core.patch`, `smoke_13of13.log`, `wdet_ed1_replay.log`, `twins_guard.log`, `g7/`

## Headline — per-gate results

| gate | rule (prereg) | result | receipt |
|---|---|---|---|
| **F10** upstream/pin | smoke 13/13 at the pinned commit | **PASS** | `smoke_13of13.log` (13/13) |
| **W-DET** hash canary | deterministic arm reproduces E-D1 `8c8a54a43f10`, var=0 | **PASS** | `wdet_ed1_replay.log` |
| **F3** world uniqueness | ≥ 90 % unique world hashes @ eval 100 | **PASS** (16/16 = 100 %) | `mini_world_report.json:f3` |
| **H4** variance real | std{position@1000, growthAt} > 0 over W-STO | **PASS** (14.05, 214.8) | `mini_world_report.json:h4` |
| **F8** rng-leak A/B | reflex determinacy(STO) ≥ determinacy(DET) − 0.05 | **PASS** (0.469 vs 0.445; Δ **+0.024**) | `mini_world_report.json:f8` |
| **F6** mismatch pre-gate | KS(sim vs real) rejects equality (p ≤ 0.05) | **PASS** (p = 0.000 both sockets, salience+food) | `mini_twins.json:f6` |
| **F1** co-tenancy/OOM | guard device + free-VRAM watch, no OOM | **PASS** (min free 1218 MiB, no breach) | `g7/guard_summary.json` |
| **GPU-SEED LAW** | per-socket training-seed std ≠ 0 | **PASS** (no zero-std socket) | `mini_twins.json` |
| **G7** energy | one watt-receipt@1, no receipt = VOID | **PASS** (schema-valid) | `g7/g7-wr-d2-firstbuild-twins-1790895965.json` |
| **F4** estimator flag | log2\|O\| < 1 flagged | **FLAG** (reflex \|O\|=2 → log2\|O\|=1.0) | `mini_world_report.json` |
| **H5** determinacy stable | spread over 3 input dists ≤ 0.15 | **REPORT: 0.50 / 0.52 — NOT STABLE** | `mini_world_report.json:h5wiring` |
| **H6** range | max−min determinacy ≥ 0.5 | **FAIL 0.118** (fire-out) / **PASS 0.648** (rule-out) | `mini_world_report.json:h6wiring` |

**W-DET (exact):** arm A, seeds 101/118/135 → `hash = 8c8a54a43f10` for all three; `r2.var_A = var_D = 0`;
R5 replay BYTE-IDENTICAL; chain OK. Devation would have been VOID — none observed.

**F8 diagnosis (patch changed during the build):** first cut injected ±60/1000 salience noise that could
cross the reflex 0.8 threshold; that produced a spurious pooled fine-grained drop (0.970 → 0.723, VOID).
Cause was the estimator conditioning on the *raw salience integer* (an alphabet that explodes only under
noise → F4/H5 instability), not an rng leak into a cell. The patch now **clips the sensor jitter so it
cannot cross the 0.8 reflex boundary** (documented in `d2_stochastic_core.patch`), and the frozen
declared-alphabet protocol gives a stable Δ = **+0.024**. Still booked as a *wiring decision*, not a KEEP.

## Mini-arm numbers (18 trainings = 2 sockets × 3 conditions × 3 seeds; eval on 4 held-out REAL test worlds)

| socket | nerr real | nerr sim | nerr sim-mis | **gap_sim** | gap_mis | control widens | det (operational) |
|---|---|---|---|---|---|---|---|
| `reflex.orient` | 0.0035 | 0.390 | 0.469 | **0.387** | 0.466 | **+0.079 ✓** | 0.469 |
| `memory.episodic` | 0.2155 | 1.550 | 2.117 | **1.335** | 1.901 | **+0.566 ✓** | 0.352 |

- **Direction (n=2, NOT adjudicated):** gap rises as determinacy falls (0.387 → 1.335) — consistent with
  H-TRANSFER's predicted negative ρ. Two points cannot adjudicate H1; recorded as directional only.
- reflex nerr_real ≈ 0 (3.5e-3) because the high-determinacy socket is a near-exact function on real
  worlds — the predicted "near-1 socket transfers near-perfectly" behaviour, in miniature.
- **Wh (measured, G7):** **0.9741 Wh** (3506.76 J; 47.14 W mean; 74.4 s wall; 55.1 GPU-s; min free VRAM 1218 MiB; max temp 76 C).

## Patch (driver-side only, behind the flag)

`dba/core.mjs` gains `opts.stochastic` (default `false` ⇒ unmodified path **byte-identical**). All rng
draws happen in the **world tick** (`step §0`): respawn-delay jitter (−5..+5 evals), probabilistic
curriculum switch (`switchDraw < 0.9`), and ±60/1000 sensor-salience noise that is **boundary-clipped at
0.8** so it cannot flip the reflex socket (F8). Reward-drift timing is **not implemented** in the mini
(fourth injection point deferred to v1) — receipted gap, not a silent one.

## Failure modes walked

- F3 ✓ (uniqueness), F1 ✓ (guard no-OOM; co-tenant CUDA PID recording is guard's own device field),
  F6 ✓ (KS rejects), F8 ✓ (after the boundary clip), F10 ✓ (pin + smoke), F4 ⚠ flag, F5 (disjointness
  assert) exercised implicitly by the 12/4 world split; F9 (activation budget) respected (≤1 M params/len;
  tiny MLP 9→32→32→1); F2 (seat) n/a — v1 seat-free, no LLM touched; F7 (growth starvation) n/a in mini.

## What v1's 200-world run needs next

1. **Freeze the determinacy estimator first.** H5 (spread 0.50/0.52) and H6 (0.118) do not pass at the
   mini's small alphabets — the measure is the prerequisite, and it is currently the weakest link. Fix
   before firing: larger/declared output alphabets, explicit support handling, and the reflex
   fire-vs-rule output choice frozen in the prereg (the two differ: 0.469 vs 1.000).
2. **All 6 sockets + W-MIS arm at 200 worlds** (140 train / 60 test), 6×3×3 = 54 twins; bootstrap CI over
   worlds on ρ; H1/H2/H3 adjudication. Growth to 1000 only if v1 passes H4 **and** CI width > 0.40.
3. **H-GROWTH receipts per world** (gated ≥ 80 %, unguided ≤ 20 %) — the mini records `grew` counts
   (15/16 both arms at 1000 evals) but not the gated/unguided split at 200-world scale.
4. **Open wiring decision for v1:** the E-D1 hash canary lives on the *engine-sheet* path
   (`experiments/e_d1_stages.mjs`), while the prereg's stochasticity injection points and the socket
   traces live on the *core.mjs Driver* path. v1 must state which path is the trace source (or keep
   the canary as a cross-path wiring check, as done here).
5. Carry forward: F9 activation-budget assert in the twin script; F5 world-disjointness assert at load
   (fail loud); the sensor-jitter boundary clip must be re-derived as a documented patch invariant.

*Not committed (lane rule). Concurrent sibling lane also wrote `fb_*.json` + `guard/` into this dir;
those are not this lane's artifacts.*

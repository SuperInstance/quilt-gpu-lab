# T5 — the dial controller (resolution↔framerate as a behavior, not a rendering parameter)

**status: ready-for-dev** (written before any t5 code exists)
**date:** 2026-09-28 (~19:55 AKDT)
**baseline_revision:** e8cf71c (head at plan-write time)
**science:** `~/projects/chiaroscuro-embedding/SEED.md` wave-5 (the 5th dimension: the sensory budget allocation itself) + wave-4 (confirm until surprised, then earn the moment)
**question:** under a FIXED compute budget (total pixel-throughput constant), does a surprise-driven controller that TRAVERSES the resolution↔framerate axis beat every FIXED allocation point on the regimes that matter — and does it do so while sitting meaningfully below a cheating oracle (proving the win is real, not an artifact of a weak ceiling)?

---

## 1. The hypothesis (frozen)

The generalized saccade: **still → slide r up** (high-res/low-fps, CONFIRM mode: verify the running simulation cheaply and precisely); **moving/surprised → slide r down** (low-res/high-fps, PREDICT mode: extrapolate fast so you don't get blindsided). If the dial is a real behavior, an adaptive allocation should dominate every fixed point on surprise-weighted error at equal budget.

## 2. The sim (frozen)

CPU-only numpy. No GPU, no frames rendered to disk — the scene is a phase-space superposition whose **pixel-space MSE is computed in closed form** (exact, no approximation: a sinusoid component with amplitude A shifted by Δφ contributes exactly `2A²(1−cos Δφ)` pixel MSE).

**Scene:** K=4 components, amplitudes `A = [1.0, 0.8, 0.6, 0.5]`, weights `w = A²`. State = per-component phase φ_i(t). Dynamics: per-component OU velocity,
- **quiescent:** τ=2.0 s, σ=0.12 rad/s (slow drift — confirmable)
- **burst:** τ=0.08 s, σ=1.4 rad/s (fast stochastic motion — must be extrapolated)
- regime schedule: quiet U(4,9) s ↔ burst U(0.8,2.5) s, alternating, per seed. dt = 1/40 s, T = 120 s (4800 ticks).

**The budget (Casey's example, frozen):** 20 points/second = 0.5/tick = 2400 points/run.
- CONFIRM: res 4 → cost 4/frame at 5 fps (every 8 ticks) = 20 pts/s
- PREDICT: res 1 → cost 1/frame at 20 fps (every 2 ticks) = 20 pts/s
- MID: res 2 → cost 2/frame at 10 fps (every 4 ticks) = 20 pts/s

**Observation physics:** an acquisition at res level r observes φ + Gaussian noise σ_r, **independent per component**: σ_hi = 0.015, σ_mid = 0.05, σ_lo = 0.12 rad (blur = phase-estimation noise; low-res is 8× noisier than foveal). Every arm sees the world only through its own acquisitions. No arm sees regime labels.

**Perception (identical machinery for every arm):** constant-velocity extrapolation. At acquisition: innovation vs current prediction; `v_inst = Δφ_obs/Δt_obs` clipped ±3 rad/s; `v̂ ← 0.6·v_inst + 0.4·v̂`; state resets to the observation. Between acquisitions: φ̂ += v̂·dt.

**Arms (6):**
1. **all-confirm** — fixed CONFIRM cadence (the map-maker)
2. **all-predict** — fixed PREDICT cadence (the insect eye)
3. **all-mid** — fixed MID point (the compromise)
4. **random** — Markov mode flips, P=1/60/tick (mean dwell 1.5 s), ledger-spent
5. **ORACLE** — mode(t) = PREDICT iff regime(t)=burst, instant switching, ledger-spent. **Cheats by design — the ceiling.**
6. **ADAPTIVE** — the dial controller: surprise z = EMA(0.3) of mean_i((innov_i/σ_mode)²) at each acquisition. z>4 → enter PREDICT. z<1.5 for 20 consecutive observations → return to CONFIRM. Min dwell 30 ticks per mode. Starts CONFIRM (still → verify). **Sees only its own innovations — nothing the fixed arms don't.**

**Ledger** (switching arms only; fixed arms are exact-cadence): income 0.5/tick, balance capped at 8.0, init 4.0; acquire only when affordable. Fixed-arm spend is exact by construction; all spends reported.

## 3. Metric (frozen)

- **error:** e(t) = Σ_i 2A_i²(1−cos(φ̂_i(t)−φ_i(t))) — exact pixel MSE.
- **surprise:** s(t) = Σ_i w_i·(φ_i(t)−φ_i(t−10))² (true velocity over the last 0.25 s; ground-truth-derived, applied identically to all arms post-hoc — pure scoring, zero control leakage).
- **weight:** u(t) = clip(s(t)/median(s) − 1, 0, 5)/5; **W(t) = 1 + 4·u(t)** — surprises hurt up to 5× more, never infinitely; verification still counts everywhere.
- **PRIMARY: SW-MSE** = Σ W(t)·e(t) / Σ W(t) over t ≥ 0.25 s.
- Secondary (descriptive): raw MSE; per-regime (quiet/burst) raw MSE; spend parity; for switching arms: switches, time-in-PREDICT, burst precision/recall, onset→PREDICT latency.

## 4. THE GATE (pre-registered, frozen — verdict vocabulary KEEP/KILL/INCONCLUSIVE only)

Official fire: seeds **{41, 42, 43, 44, 45}**, T=120 s each, arm-specific RNG streams. Aggregate = **mean over the 5 seeds**. Let `adaptive` = adaptive mean SW-MSE, `best_fixed` = min over arms 1–4 means, `oracle` = oracle mean.

- **WIN:** `adaptive < 0.98 × best_fixed` (beats ALL four fixed arms by ≥2%)
- **CEILING:** `oracle < 0.95 × adaptive` (oracle meaningfully better — headroom exists, the win is real and not "the task is trivially easy")
- **ROBUST:** adaptive beats its per-seed best-fixed arm in **≥4 of 5 seeds**
- **PARITY:** every arm's total spend within [0.95, 1.05]×2400 points
- **KEEP-iff:** WIN ∧ CEILING ∧ ROBUST ∧ PARITY
- **KILL-iff:** any fixed arm has mean SW-MSE ≤ 1.02 × adaptive (a fixed point matches the controller — the dial is not earning its keep)
- **INCONCLUSIVE:** otherwise (including: adaptive beats all fixed but oracle ≈ adaptive — ceiling too weak to certify the win)
- **Never loosen.** These numbers were frozen before any t5 code exists. A result between the bands is INCONCLUSIVE, not KEEP-with-an-asterisk.
- **VOID condition:** missing artifact files (`experiments/t5_dial_controller.py`, `results/t5_dial_controller.json`), spend-parity failure, or any arm crashing → the fire is VOID, no verdict claimed.

---

## 7. FIRE 1 — ABORTED (2026-09-28 ~20:05 AKDT, before any v2 refire)

**What happened:** fire 1 ran; the controller made 1 switch in 120 s (~15 bursts in-schedule), sat 49% in PREDICT, and its quiet-regime MSE matched all-predict — it entered PREDICT at the first burst and never returned. Fire-1 official numbers (seeds 41–45, preserved for the record): all-confirm 0.01317 · all-predict 0.03896 · all-mid 0.01094 · random 0.03305 · oracle 0.01960 · adaptive 0.03891 (SW-MSE means) — voided by the defect below, no verdict claimed.

**Diagnosis (config bug, not a finding — G9 precedent):** the frozen estimator (`v_inst = Δφ/Δt_obs` clipped ±3 rad/s, `v̂ ← 0.6·v_inst+0.4·v̂`) is self-contradictory with the frozen exit threshold. In PREDICT mode the finite-difference velocity noise is `σ_lo·√2/0.05 ≈ 3.4 rad/s` — above the ±3 clip — so per-tick innovations carry `≈ v̂_noise·0.05` of injected noise and `z_ema` floors at ≈1.5–2.5, **above** Z_EXIT=1.5. The designed hysteresis ("decay below → confirm-mode") was unreachable; fire 1 tested a stuck controller, not the hypothesis.

**v2 repair (documented before refire; gate/scene/budget/thresholds/seeds UNTOUCHED):**
- The shared per-arm predictor (identical machinery for all six arms) is replaced by a 2-state steady-state Kalman filter `[φ, u]` — the principled form of the plan's own prose ("constant-velocity extrapolation", "surprise = prediction error vs the mode's noise floor"). Process prior `q = 2σ²/τ` from the **quiet** OU (0.12², 2.0 s) → `q = 0.0144` rad²/s³: every arm's filter assumes the expected (quiet) world; bursts are precisely the model violation the surprise detector exists to catch.
- Surprise is the **normalized** innovation: `z_raw = y²/S` with `S = P₀₀ + σ_res²` — the filter's own uncertainty, so thresholds (4.0 / 1.5 / 20 obs / 30-tick dwell) keep their meaning and the hysteresis becomes expressible in both modes.
- Arms differ ONLY through (σ_res, cadence) via R and update frequency — same symmetry as v1. The ±3 clip and α=0.6 are deleted.
- Switch/oracle/random mode statistics are counted post-hoc from the logged mode arrays (v1 under-counted non-adaptive arms).

The gate in §4 is unchanged: WIN 0.98, CEILING 0.95, KILL 1.02, ROBUST 4/5, PARITY ±5%. Whatever v2 says, v2 says.

**Smoke gate (before the real fire, seed 999, 30 s, NOT tuned on):** all six arms produce finite numbers; adaptive switches mode ≥1 time; no NaNs.

## 5. Budget (frozen)

CPU-only numpy, 6 arms × 5 seeds × 4800 ticks ≈ 144k arm-ticks — target < 2 min wall on the eileen box.

## 6. Honesty clauses

- The controller's only inputs are its own observations and its own prediction errors — the same information stream its fixed cousins receive at their cadences. Only the ORACLE sees regimes (that is what makes it the ceiling).
- Surprise weighting is applied post-hoc and identically to all arms; it cannot favor any arm's allocation.
- Switching latency and hysteresis losses are real costs the adaptive arm pays and the oracle mostly avoids — that gap is part of the finding, either way.

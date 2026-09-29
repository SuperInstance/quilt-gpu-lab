# T5b — the trackability horizon sweep (the boundary map of the 5th dimension)

**status: ready-for-dev** (written before any t5b code exists)
**date:** 2026-09-28 (~20:50 AKDT)
**baseline_revision:** ab8ec08 (head at plan-write time)
**science:** t5 verdict KILL (results/t5_dial_controller.json): all-confirm 0.0230 beat oracle 0.0436 and adaptive 0.0703 — the frozen burst regime was white-jerk motion (OU τ=0.08 s: velocity decorrelates inside one confirm-sampling interval, nothing to extrapolate). The t5 RESULTS note pre-registered this follow-up: sweep burst τ to locate "the boundary where the dial starts paying."
**question:** WHERE does the resolution↔framerate dial start paying? Sweep the burst motion correlation time τ_motion and map, per τ, whether the surprise-driven controller beats every fixed allocation under the same frozen gate family. THE answer: the **trackability horizon** — the smallest τ at which adaptive first beats all-confirm, i.e. where τ_motion starts dominating the confirm channel's sampling timescale (cadence 8 ticks = 0.2 s).

---

## 1. The sim (frozen — identical to t5 v2, ONE changed knob)

Everything is the frozen t5 v2 sim (proposals/runs/t5-plan.md §2, as implemented and fired in
experiments/t5_dial_controller.py): K=4 sinusoidal components, A=[1.0,0.8,0.6,0.5], w=A²,
dt=1/40 s, T=120 s (4800 ticks), budget 20 pts/s (2400/run), CONFIRM hi/4pts/every-8-ticks,
MID 2pts/every-4, PREDICT lo/1pt/every-2, σ_hi=0.015/σ_mid=0.05/σ_lo=0.12, quiet OU (2.0 s, 0.12 rad/s),
regime schedule quiet U(4,9) s ↔ burst U(0.8, 2.5) s, v2 per-arm steady-state Kalman estimator with
quiet-world prior q=0.0144, exact closed-form pixel MSE e(t)=Σ2A²(1−cos Δφ).

**The one free knob:** burst OU correlation time. Per sweep point, `OU_BURST = (τ, 1.4)` with

**τ ∈ {0.08, 0.2, 0.5, 1.0, 2.0, 4.0} seconds** (ascending grid), σ_burst **frozen at 1.4 rad/s** (t5's value), quiet OU **untouched**. Nothing else changes.

**Paired-truth property (frozen, load-bearing):** the RNG draw order in `simulate_truth` is
identical across τ for a given seed (2 uniforms per regime cycle, then K draws for φ₀, K for u₀,
one `standard_normal(K)` per tick regardless of regime). So each seed has the SAME burst schedule
and the SAME underlying standard-normal stream at every τ; only the OU filter constants differ.
The sweep is paired per seed across τ.

**The controller never sees τ.** All thresholds, the Kalman prior, cadences — everything is t5-frozen
in every world. This is a domain map of a fixed brain across worlds, not a per-world tune.

## 2. Arms (six per τ, frozen)

1. **all-confirm** — fixed CONFIRM cadence (exact spend)
2. **all-predict** — fixed PREDICT cadence (exact spend)
3. **uniform** *(replaces t5's all-mid in the roster — a spread strategy, not a third fixed point)*:
   deterministic round-robin over dial positions [CONFIRM, MID, PREDICT]; the cursor advances only
   on a **successful** acquisition (ledger spend), so realized points split ~evenly across the three
   dial positions; if the ledger cannot afford the current position the arm retries it next tick.
   Ledger arm (income 0.5/tick, cap 8, init 4). Arm-RNG offset 77 (never drawn — deterministic).
4. **random** — t5 Markov flipper, P=1/60/tick, ledger
5. **oracle** — PREDICT iff burst, instant, ledger. Ceiling.
6. **adaptive** — t5 v2 controller verbatim (z=EMA(0.3) of normalized innovation; enter PREDICT at
   z>4; exit after 20 consecutive obs below z<1.5; min dwell 30 ticks; starts CONFIRM).

**FIXED set for the gate:** {all-confirm, all-predict, uniform, random}.

## 3. Metric (frozen — t5 §3 verbatim)

SW-MSE with surprise s(t)=Σw_i(φ_i(t)−φ_i(t−10))², u(t)=clip(s/median−1,0,5)/5, W=1+4u;
secondary raw/quiet/burst MSE, spend ratio, switch stats, burst precision/recall, onset latency.

## 4. THE GATE (frozen — t5 §4 gate family applied PER τ, verdict vocabulary KEEP/KILL/INCONCLUSIVE)

Official fire per τ: seeds {41,42,43,44,45}, T=120 s, arm-RNG offsets as in t5 (+77 for uniform).
Aggregate = mean over the 5 seeds. `adaptive`/`best_fixed`/`oracle` are per-τ means; best_fixed = min
over the four FIXED arms.

- **WIN:** adaptive < 0.98 × best_fixed (beats ALL four fixed arms by ≥2%)
- **CEILING:** oracle < 0.95 × adaptive
- **ROBUST:** adaptive beats its per-seed best-fixed arm in ≥4 of 5 seeds
- **PARITY:** every arm's total spend within [0.95, 1.05] × 2400
- **KEEP-iff:** WIN ∧ CEILING ∧ ROBUST ∧ PARITY
- **KILL-iff:** any fixed arm mean SW-MSE ≤ 1.02 × adaptive
- **INCONCLUSIVE:** otherwise
- **Never loosen.** A τ-row between bands is INCONCLUSIVE, not KEEP-with-an-asterisk.

**"The dial pays at τ" := WIN(τ) is true.** (Task definition: adaptive must beat ALL fixed strategies.)

**THE answer — trackability horizon (frozen definitions, all reported):**
- **horizon τ\*:** the smallest τ in the ascending grid with `adaptive_mean(τ) < allconfirm_mean(τ)`
  (raw beat of the t5 winner — the boundary asked for). If adaptive beats all-confirm at τ=0.08
  already, τ\*=0.08; if never, τ\*=none.
- **pays τ:** smallest τ with WIN(τ) true (may be ≥ τ\*).
- **sub-grid crossing estimate (descriptive only):** linear interpolation of the ratio
  r(τ)=adaptive/all-confirm in log τ between the bracketing grid points where r crosses 1.0.
- Non-monotonicity is reported as-is: "first" means smallest grid τ, full per-τ table is the artifact.

**VOID condition (whole run):** regression-gate failure (§5), smoke failure on any τ without a
recorded withhold, missing artifact files, spend-parity failure, or any arm crash → no verdict claimed.

## 5. Honesty gates (frozen, run before the official fire)

1. **py_compile:** `python3 -m py_compile experiments/t5b_tau_sweep.py` before any run.
2. **REGRESSION vs t5 (bitwise):** at τ=0.08, seed 41, for the five arms shared with t5
   (all-confirm, all-predict, random, oracle, adaptive) the t5b re-implementation must reproduce
   `t5_dial_controller.run_arm` outputs EXACTLY (error arrays `np.array_equal`, stats dicts equal).
   This proves the copied per-tick loop is faithful; t5's files themselves are never modified
   (the sweep sets the burst-τ knob on the *imported module object* at runtime only).
3. **SMOKE per τ:** seed 999, 30 s: all six arms finite; adaptive switched ≥1; frac_predict < 0.9.
   A τ whose smoke fails has its official fire withheld and is reported VOID.

## 6. Budget

CPU only, system python3 + numpy. 6 τ × 6 arms × 5 seeds × 4800 ticks ≈ 864k arm-ticks; t5's
30-run official fire took 2.3 s wall → target < 30 s total. No GPU (owned by K2).

## 7. Artifacts & discipline

- `experiments/t5b_tau_sweep.py` (the only new code)
- `results/t5b_tau_sweep.json` (per-τ arms/gate/table + horizon + smoke + regression receipts)
- dated RESULTS.md block with the one-line answer and the per-τ table
- pathspec-scoped commit + push of ONLY these files (+ this plan). No t5 file touched.
- No tuning on official seeds; grid and gates frozen by this document before any t5b code existed.

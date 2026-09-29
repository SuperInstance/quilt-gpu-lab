# IB1b — the fly-rule under variable delay + nonlinear structure

**status: ready-for-dev** (written 2026-09-28 ~20:50 AKDT, before any IB1b code exists)
**baseline_revision:** a5e6f7f (K2 preflight bug fix head)
**parent:** IB1a (KEEP — A 0.3733 vs B 0.2583 / C 0.2717, D-parity 0.3717; `results/ib1a_fly_rule.json`)
**question:** does the fly's order-gated δ-broadcast still beat its controls when (1) receipts arrive at
**variable** delay (uniform 1–5 steps, resampled per receipt — no timestamps to look up, the trace must
carry the credit alone) and (2) the correct-action map is **nonlinear** (random 2-layer MLP, not linear argmax)?

This is the hardening IB1a's own RESULTS block queued: "IB1b: variable delay + nonlinear structure."

## 1. Hardening deltas vs IB1a (the only two changes)

1. **Variable delay.** Each action at step t earns reward r determined immediately, but the receipt
   (r, a₀) is **delivered at t+d, d ~ Uniform{1..5} resampled per action**. The agent has no delay
   clock; the per-action eligibility trace is the only bridge. (IB1a: fixed d=3, exact hist lookup.)
2. **Nonlinear world.** correct(x) = argmax( ReLU(x·W₁)·W₂ ), W₁ ∈ R^{50×16}, W₂ ∈ R^{16×8},
   standard normals, frozen per seed. (IB1a: argmax(x·W), linear.) Reward reliability 80/20 unchanged.

Everything else frozen at IB1a values: PN 50 → KC 2000 (~10 PN/KC, row-normalized), k-WTA top 160,
V ∈ R^{2000×8} (~16k params, the only plastic matrix in A/B/C), ε-greedy 0.1, T=600, 200 train /
100 held-out contexts (6-of-50 active, N(0,1)), seeds {2718, 42, 1337}, CPU numpy only.

## 2. Arms (frozen)

Per-tick sequence (identical machinery across arms; the ONLY differences are marked):

1. **Deliver receipts scheduled for t** — traces still reflect coincidences through t−1 (strictly
   pre-δ; the tick's own coincidence has not been written yet).
2. **Act:** kc = k-WTA(x_t); a = random w.p. ε else argmax(kc·V).
3. **Trace update (all fly arms):** E ← λ·E; E[:,a] += kc. λ = 0.9 (λ⁵ ≈ 0.59 at the longest delay).
   - **B (no-third-factor):** identical trace, but plasticity is `V[:,a] += η·E[:,a]` every tick,
     clip ±2 — i.e. A with δ replaced by the constant +1. No reward information enters anywhere.
     (IB1a's B used instantaneous kc; the trace version isolates the δ as the single difference.)
4. **Receipt processing** (arms A, C):
   - v̂ = V[:,a₀]·E[:,a₀]; δ = r − v̂ (same in both — the difference is ONLY what the δ is spent on).
   - **A (fly-rule):** spend immediately on the pre-coincidences: `V[:,a₀] += η·δ·E[:,a₀]`.
   - **C (order-swapped):** spend nothing now; `δ_trace += δ`. On every tick that receives no
     receipt, after step 3: `V[:,a_t] += η·δ_trace·E[:,a_t]`, then `δ_trace ← 0.9·δ_trace`.
     Each δ is spent on *later* coincidences (anti-causal; the Hige 2015 odor-after-DAN pairing).
5. **Homeostasis:** A and C: `V *= (1 − 2e-4)` every tick. B: clip only (IB1a convention).

**D (matched backprop with replay, reported ungated):** same frozen encoder (separate seed+1 draw,
IB1a convention) → numpy 2-layer MLP 2000→64 ReLU→8 (~128.6k params — disclosed, bigger than A's 16k;
IB1a's D-advantage precedent), Adam lr 1e-3, replay buffer 32, minibatch 16, MSE on the taken action's
q toward r. **D experiences the same variable-delay receipt schedule:** choice stores (h_t, a_t) at t;
the receipt at t+d pushes (h_t, a_t, r) into replay — the buffer is D's stand-in for the trace.
**No torch:** system python3.14 has numpy only (torch dist-info is orphaned; GPU belongs to K2).
Backprop is manual (analytic gradients); a finite-difference gradient check (rel err < 1e-4) runs
before the fire. This is IB1a-plan precedent: "no gradient of any kind in A/B/C; numpy only."

## 3. THE GATE (frozen before any IB1b code — identical to IB1a's, per task directive)

Primary metric: mean reward over the last 200 steps, averaged over 3 seeds → Ā, B̄, C̄, D̄.

- **KEEP iff Ā − B̄ ≥ 0.05 AND Ā − C̄ ≥ 0.05.** Binary; no INCONCLUSIVE band (task froze the IB1a
  gate form; never loosened, never reinterpreted after the fire).
- **A vs D: reported honestly, ungated.** D's number is the price tag of "no backprop", not a gate condition.
- **Sanity annotation (descriptive, does not alter the verdict):** if D̄ ≤ chance + 0.02
  (chance = ⅛·0.8 + ⅞·0.2 = 0.275, so D̄ ≤ 0.295), the verdict stands as computed but is annotated
  "world-too-hard" — even backprop couldn't learn this world, so the arm separation is weak evidence.

**Verified-fire chain (pre-registered):** (1) write code; (2) `py_compile`; (3) finite-difference
gradcheck of D's manual backprop (< 1e-4 rel err); (4) smoke: T=300, 1 seed, all arms finite,
wall-time sane; (5) full fire; (6) JSON + dated RESULTS.md block; (7) pathspec-scoped commit + push
of ONLY: this plan, `experiments/ib1b_variable_delay.py`, `results/ib1b_variable_delay.json`, RESULTS.md.

## 4. Predictions (before the fire, for the record)

- Margins compress for everyone vs IB1a: 3 visits/context under 80/20 noise + a nonlinear target is a
  harder fit for all four arms; D's replay+capacity should keep it at or above the fly arms.
- A should still separate from B (B has no reward signal at all — it cannot even track the map) and
  from C (C's δ lands on later random contexts — scrambled credit is worse under variable delay
  because the spending window is unmoored from any fixed structure).
- The trace mechanism is now load-bearing in a way IB1a's timestamp lookup was not: if A fails here,
  the fly rule's viability under realistic receipt jitter dies honestly and IB1c must rethink the
  trace (longer λ, announced-receipt tokens), not the bookkeeping.

## 5. Artifact discipline

Plan (this file) before code; code before fire; JSON written by the script itself (stdlib JSON,
no float32 leaks); dated RESULTS.md block with verdict + real numbers for all four arms;
pathspec-scoped commit. IB1a's files are touched by nothing in this run.

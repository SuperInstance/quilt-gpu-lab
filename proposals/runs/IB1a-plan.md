# IB1a — the fly's no-backprop learning rule on delayed receipts

**status: ready-for-dev** (flipped from draft 2026-09-28 ~19:50 AKDT after a full re-read of the frozen numbers; gate unchanged)
**date:** 2026-09-28 (written before any IB1a code exists)
**baseline_revision:** edb96bd81c364982c180aa66b23689c13e22e055
**science:** `docs/insect-learning-science-2026-09-28.md` §6 (the implementable rule) + `docs/quilt-insect-brain-2026-09-28.md` (IB1–IB5 seeding)
**question:** is the fly's third factor — and its temporal ORDER (pre-before-DAN, Hige 2015) — load-bearing where credit assignment is real, i.e. when the receipt (reward) arrives k steps after the choice?

---

## 1. The problem (frozen)

**Delayed-receipt contextual bandit.** Each episode is 3 ticks:

- **t0 (choice):** context token `c` ∈ 16 shown (one-hot). Agent picks action `a0` ∈ 5.
- **t1 (filler):** the `wait` token shown (same every episode — a state with no payoff-bearing information, present so receipt-time co-occurrence is *not* the decision-time coincidence). Agent picks `a1` (no payoff consequence).
- **t2 (receipt):** the `receipt` token arrives **with** the reward: `r = +1` if `a0 == π*(c)` else `r = −1`, where `π*` is a fixed random context→action map. **The receipt is 2 steps after the choice.** Credit must cross the delay.

Chance performance (uniform policy): `E[r] = 0.2·(+1) + 0.8·(−1) = −0.6`. Ceiling `+1.0`.

Why this problem: with the receipt 2 steps after the choice, a learner can only bridge the delay with a *temporal* mechanism (eligibility trace). Co-occurrence-at-receipt credits the wrong coincidence (t1/t2 states, not the t0 choice); a swapped-order rule spends each δ on *later* coincidences (scrambled across episodes). This is exactly where the third factor should matter.

## 2. The agent (fly-scale honest, frozen)

Per the science doc §6 pseudocode, with two pre-registered deviations noted:

- **Encoder (birth-frozen, never trained, seed recorded):** `N_IN = 18` tokens (16 contexts + `wait` + `receipt`), `K = 2000` KCs, **10 random inputs per KC** (Turner 2008 fan-out), nonzero weights ~ U(0.5, 1.5).
- **k-WTA:** keep top **100** KCs (5%, fly-scale ~5%) per tick.
- **Readout (the only trained matrix):** `W ∈ R^{2000×15}`, `y = ReLU(W @ kc)`. **V = 15 compartments = 5 action slots × 3 valence channels (appetitive, aversive, o).** The `o` channel is present (fly-honest 15-compartment count) but contributes nothing to policy or updates — pre-registered as inert.
  - Policy: `score_a = y[a,app] − y[a,av]`; `softmax(score/τ)`, τ = 0.5 constant, all arms.
  - **DEVIATION (disclosed):** the task hint said "~2–6k params"; K·V = 2000×15 = **30,000** trainable floats. The science doc §6 explicitly blesses fly-scale (2000×21 = 42k ≤ 1M budget) and the task title says fly-scale honest. We take 30k. Only ~100 KC rows are ever active per tick; updates touch only trace-carrying rows.
- **Eligibility trace:** `e ← λ·e + outer(kc, y)` every tick (pre×post coincidence — Gerstner neoHebbian frame). **λ = 0.9** frozen (delay 2 → t0 trace weight λ² = 0.81 at receipt).
- **Third factor δ (the receipt/dopamine):** RW form, `δ = r − r̄`; `r̄ ← r̄ + β·(r − r̄)` per receipt, β = 0.02 (prediction-accuracy re-evaluation, Felsenberg flavor).
- **Arm A update (order-gated):** at every tick first `e ← λ·e + outer(kc,y)`; if a receipt event occurs this tick:
  `W[a,app] += η·δ·e[a,app]`; `W[a,av] −= η·δ·e[a,av]`; `o` untouched; then
  `W ← clip(W, 0, 5)` and **active forgetting** `W ← (1 − 3e-5)·W` per receipt event (all arms get this identical schedule — the modulator is also the forgetting signal).
  **Strict order gate:** only coincidences accumulated in `e` *before or at* the DAN/receipt tick are spent. No δ, no update, otherwise.
- **Arm B (no-third-factor control):** identical arch/encoder/explorer/clip/forgetting; plasticity is pure Hebbian co-occurrence: every tick `W += η_B·outer(kc, y)` on all channels (app +, av −, same sign convention as A), no δ, no r̄. B sees receipts (and forgets on them) but they gate nothing.
- **Arm C (order-swapped control):** same as A but the δ is spent on coincidences that come **after** it: maintain `δ_trace ← λ_δ·δ_trace` per tick (λ_δ = 0.9); at a receipt tick, `δ_trace += δ` **after** that tick's coincidence; update at every (non-receipt) tick: `W += ±η·δ_trace·outer(kc,y)` with A's channel signs. The receipt tick itself updates with nothing (its δ has not preceded any coincidence yet). Same information, reversed order — the Hige 2015 odor-after-DAN pairing.
- **Arm D (matched tiny backprop agent, reported not gated):** numpy 2-layer MLP: 18 → 64 ReLU → 5 logits (+ value head 64→1), ~1.3k params (disclosed: **smaller** than A's 30k — matched on problem/input, not params). Online actor-critic, same 3-tick stream: at t0/t1 it acts via softmax (a1 unsupervised, mirrors the stream); at the receipt it updates on the **stored (s0, a0) slot** — its own memory mechanism (a 1-slot buffer; the backprop-world stand-in for A's trace, disclosed as part of the arm's definition). Advantage `r − V(s0)` (detached), critic MSE, entropy bonus 0.01. Adam. **No replay, no target net — same online stream as the fly arms.**
- **NO backprop in arms A/B/C. No gradient of any kind. numpy only.**

## 3. Budget & sweep (frozen)

- Episodes: **10,000 per run**; 3 ticks each. Seeds: **{11, 22, 33}** (encoder + `π*` + all init derive from the seed; fresh problem per seed).
- η grid (selected per arm by the **primary metric itself**, mean reward over the last 2,000 episodes — same criterion for every arm, symmetric, disclosed as mildly optimistic): A and C: `η ∈ {0.03, 0.1, 0.3}`; B: `η_B ∈ {0.003, 0.01, 0.03}` (B updates every tick, ~30× more often); D: `lr ∈ {0.01, 0.03}`.
- Total: 4 arms × ≤3 configs × 3 seeds × 10k episodes = **≤26 runs**, CPU, target < 5 min wall.
- Smoke gate (before the real fire): 200 episodes, all four arms produce finite numbers, A-arm early mean ∈ [−0.9, −0.3] (≈ chance −0.6 ± slack).

## 4. THE GATE (pre-registered, frozen — verdict vocabulary KEEP/KILL/INCONCLUSIVE only)

Primary metric: **mean reward over the last 2,000 episodes**, averaged over the 3 seeds, per arm. Call these `Ā, B̄, C̄, D̄`.

- **KEEP-iff:** `Ā − B̄ > 0.30` **AND** `Ā − C̄ > 0.30` **AND** `Ā > 0.0` — the third factor and its ORDER are both load-bearing, and the fly rule actually learns.
- **KILL-iff:** `Ā − B̄ < 0.10` **OR** `Ā − C̄ < 0.10` — either the third factor or its order fails to carry the credit assignment.
- **INCONCLUSIVE:** otherwise (between the bands). Report both deltas, no verdict inflation.
- **A vs D: REPORTED HONESTLY, NOT GATED.** Backprop may win at this scale; the point is what the fly rule achieves *without* it. `D̄` is recorded in the JSON beside the gate arithmetic.
- **Never loosen.** Margins were fixed before any IB1a code existed. If the result lands between the bands, the verdict is INCONCLUSIVE, not KEEP-with-an-asterisk.

Secondary (descriptive only): optimal-action rate over the last 2,000 episodes (chance 0.2), per-1000-episode reward curves, final `r̄`.

## 5. Artifact discipline

- Plan (this file): `proposals/runs/IB1a-plan.md` — flipped to `ready-for-dev` before any experiment code is written.
- Code: `experiments/ib1a_fly_rule.py` (numpy-only, stdlib JSON; no float32 leaks into JSON — the E1 lesson).
- Results: `results/ib1a_fly_rule.json` (every arm, every seed, the frozen gate, the verdict computed by the script itself).
- Ledger: dated entry in `RESULTS.md` with verdict + numbers + all four arms.
- Commit: pathspec-scoped (plan + code + results + RESULTS.md only). Halt points leave durable artifacts.

## 6. Predictions (written before the fire, for the record)

- A should climb from −0.6 toward > 0.5 (16 one-hot contexts are nearly orthogonal after the random expansion + k-WTA; a linear readout separates them — that is the Caron/Turner mechanism doing its one job).
- B should hover near chance: co-occurrence at t1/t2 credits states that carry no decision information, and its t0 loop is outcome-blind policy tracking.
- C should hover near chance or below: each δ lands on the *next* episode's random context — scrambled credit.
- D should reach ceiling fastest (a perfect memory slot + gradients). Its number is the honest price tag of "no backprop", not a gate condition.

If A fails to separate from B/C here — on a problem where the trace is the *only* bridge over a 2-step delay — the fly-rule program's first rung dies honestly and IB1b is rethought from the §6 rule, not from vibes.

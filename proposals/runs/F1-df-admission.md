# F1 — ΔF-admission scheduling falsifier (pre-registration)

**Fired from:** SCOUT-3 study (2026-09-30): the ternary-* cluster's mined claim — "schedule by
free-energy minimization −ΔF = utility − T·ΔS instead of by priority; the optimum sits at 0, not at
maximum slack." Another lane's physics; our metal tests it.
**Status:** FROZEN before fire. Post-fire changes = documented amendment only.

## The claim under test (as mined, verbatim gates)
ΔF-driven admission keeps mean wait within 5% of priority-FIFO while cutting queue-length variance
≥40% and eliminating the ≥3× depth-4 latency blowups; scheduling at budget-status +1 (slack extreme)
is ≥15% slower.

## Frozen design
- **Queue sim:** discrete ticks, single server, T=30,000 ticks, arrivals Bernoulli(0.8). Per job:
  utility u ~ Exp(1); depth d ∈ {1..6} with p = [.40,.25,.15,.10,.06,.04]; service demand per pass
  s = 1 + 0.1·d; nesting-pressure mechanism: on each completed pass, job requeues with probability
  0.05·d (same draws across arms — paired). Paired streams: same arrivals/u/d/requeue matrices per
  seed across ALL arms; 3 seeds (91, 92, 93).
- **Arms:**
  1. `pfifo` — serve max-utility, FIFO tiebreak.
  2. `df` — order key u − T·z_d, z_d = (d − 2.29)/1.43 (frozen population z-score of depth = churn
     proxy). Control parameter T read off a budget trit: queue length Q → status −1 if Q > 6,
     0 if 2 ≤ Q ≤ 6, +1 if Q < 2; T(−1)=0, T(0)=1.0, T(+1)=2.0.
  3. `slack` — T=2.0 always (the slack extreme the claim predicts is ≥15% slower).
- **Metrics:** mean wait (arrival → first service start), per-tick queue-length variance,
  depth blowup ratio r = mean_wait(d≥4)/mean_wait(d≤2), fleet completion time (last completion).

## Gates (frozen)
- **G1:** |meanwait_df − meanwait_pfifo| / meanwait_pfifo ≤ 0.05.
- **G2:** var_df ≤ 0.6 · var_pfifo.
- **G3:** premise r_pfifo ≥ 3.0; eliminated iff r_df < 3.0. If premise absent (r_pfifo < 3.0) the
  claimed regime does not reproduce in this sim — book **PREMISE-ABSENT** (a finding about the claim's
  fragility, not a pass).
- **G4:** meanwait_slack ≥ 1.15 · meanwait_df.
- **KEEP** iff G1 ∧ G2 ∧ (premise ∧ eliminated) ∧ G4. **KILL** otherwise, with the per-gate table.
  Mixed outcomes booked honestly per gate.

## Honest risks
- The churn proxy (z-scored depth) and the requeue mechanism are OUR minimal faithful reading of
  "nesting pressure"; their fleet semantics may differ. A KILL here kills the mined composition as
  specified, not their repositories.
- Single-server, ρ=0.8, no reneging — one regime. The claim is regime-scoped by construction.

## Compute
CPU seconds. Artifacts: `experiments/f1_df_admission.py`,
`results/f1_df_admission/{results.json,run.log}`.

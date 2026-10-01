# B1b-kink-head — ALTERNATE pre-registration (300-epoch arm set). **NEVER FIRED.**

**Status: archived, unreleased.** This is the alternate pre-registration written by the
first B1b subagent at ~14:56 AKDT on 2026-10-01. It was **clobbered at 14:57** by a
concurrent duplicate B1b subagent that wrote the live `proposals/runs/B1b-kink-head.md`
(which is the pre-registration the landed run uses). The alternate's fire was
**stopped at 15:07** (inner run killed 2 min in) to deconflict: two guards with the
same `task_id`/`receipt_dir` would overwrite `guard_summary.json` and invalidate the
first capstone receipt's `state_digest`. Preserved for study, per the archive rule.
Code: `_archive/b1b_kink_head.py.archived-20261001`,
`_archive/b1b_pong_law_engine.mjs.archived-20261001`.

## Design (frozen at 14:56, before its fire)

Direct follow-up to B1-DISTILL (KILL at frozen 1e-3; step-direction exact 1.0000; the
deficit is deadzone/clamp VALUE fidelity).

- **Frame: reused verbatim from B1** — uniform-random reachable states, both paddles
  U{−1,0,+1}, 240 traces × ≤1200 ticks (seed 900000+i), held out by WHOLE trace
  (i % 5 == 0), master seed 2718, train seeds 2718/2719/2720; labels executed by the
  unmodified shipped `ai.track` cell.
- **Tolerances (frozen): 1e-2 and 5e-2**, both at the same **0.99** bar.
  - 5e-2 = the tolerance at which B1's converged tanh control already reached 0.9904
    (task attainable by a correct model); 1e-2 = the discriminating gate (B1's
    converged tanh floor 0.8803, a 0.12 gap).
  - Rationale: B1's 1e-3 is ≈0.15% of a 0.7-step — a float knife-edge that measures
    the **basis**, not the distillation (B1's own 300-epoch control: 0.349 @1e-3).
- **Arms (all 300 epochs, Adam 1e-3, batch 4096, 3 seeds):**
  (a) TANH `3-64-64-1` tanh, linear head (B1's exact arch, re-scored; at 300 epochs it
      doubles as a **replication control** of B1's sensitivity control: must land on
      rms 0.02077317051589489 / 0.8803 @1e-2 / 0.9904 @5e-2 within 1e-6);
  (b) RELU `3-64-64-1` ReLU (piecewise-linear basis — the law's own function class);
  (c) KINK-RESID: ReLU trunk → learned deadzone `d` and reflex speed `k` (softplus,
      init ≈1.5 / 0.775) + linear residual `r`,
      `Δ = clamp(p + sign(b−p)·min(k, relu(|b−p| − d)) + r, [6,54]) − p`
      (a superset of the shipped law at d=1.5, k=s, r=0).
- **Training budget rationale:** B1 conflated optimization with representation at 40
  epochs; B1b must train at convergence (300) so the head class is the only variable.
- **Gate A (two tolerance gates):** mean over 3 seeds ≥ 0.99 AND std > 0 → PASS per
  gate; `std == 0 → INCONCLUSIVE` (never PASS); arm PASS iff BOTH gates PASS.
- **Per-region breakdown (new):** partition held-out ticks by the law's regime —
  clamp (binding, nonzero move) / deadzone (Δlaw == 0, incl. clamp-at-rest) /
  saturation (|b−p| ≥ 1.5+s) / ramp (1.5 < |b−p| < 1.5+s) — report per-arm agreement
  at both tolerances per region (mean±std over seeds).
- **Gate B (SECONDARY, only for arms clearing BOTH gates):** B1's identical h2h
  protocol (100 seeds × 2 swapped sides × 3 train seeds = 600 games, max 20000 ticks,
  law-vs-law control first). No PASS/FAIL gate attached.
- **Controls:** pristine-vs-switch law equivalence (bit-identical); JS-vs-torch net
  port per side at MATCHED precision (f64) < 1e-6 for every arm (the JS evaluator is
  f64; the f32 column is the ~1e-7 (smooth) / ~3e-6 (kink) evaluation gap, reported
  not gated — both far below the ~0.7 step scale).
- **Guard/G7:** `Guard(task_id="B1b-kink-head", seed=2718, receipt_dir=results/b1b_kink/guard)`,
  free VRAM ≥ 1024 MiB, temp ≤ 80 °C, retry once after 60 s else NOT-RUN; VRAM < 1.5 GB;
  co-tenancy with the 7B seat not subtracted.
- **Verdict map:** ≥1 arm PASS both → KEEP; else ≥1 clean FAIL → KILL; else INCONCLUSIVE.

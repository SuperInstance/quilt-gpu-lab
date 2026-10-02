# SYNTH-0 — big-picture synthesis, 2026-10-01 (GLM-5.3 flagship seat)

Scope: everything booked today (EST-FREEZE, B1b×2+reconciliation, B1C-hooks, D2-FIRST-BUILD A/B, D2-V1b
200-world, COMP0, COMPOSITE-1 r2, C1-PLAYTEST, HY4-TRIAL, XP-A/B/C, G1/G1b/G1c/G1d, FT-A1, A2, A5,
D12i/D12j, INSTRUMENT-01+repro, PR-HARVEST) + QUEUE + ROADMAP + pr_harvest/. Every number below is
booked; speculation is marked. NOT COMMITTED.

---

## 1. The 3–5 strongest cross-lane patterns

### P1 — The measurement layer keeps being the finding, not the model
Independent lanes, same shape:
- **EST-FREEZE:** the D2 build A/B disagreement was the *encoder* (fire|full-channel pure, spread
  0.000; fire|salience impure 0.833). FROZEN-V1 = NONE because H5 conflated estimator bias with
  genuine input-distribution sensitivity (synthetic floor ≤0.04 for E3).
- **D2-V1b:** H1 ρ=−0.37 CI[−0.60,0.60] FAIL is *dragged by H5 instability* (4/6 sockets; policy.action
  op-det 0.901 but spread 0.924 — the near-1 class itself is fragile). The lane booked this tension honestly.
- **COMP0 → COMP1:** std==0 was 66-item granularity; COMP1's 590-item + item-level bootstrap fixed it —
  the degeneracy law never fired again. Measurement fix WORKED (their words).
- **G1c/G1d:** the battery key was wrong (19/96 labels); the seat was right (0.5208 → 0.6979 corrected).
- **XP-A:** instruments given real ways-to-fail transfer 0.994 held-out; fixed pins transfer 0.000.
- **INSTRUMENT-01 repro:** per-point timing numbers are single-draw statistics (0.1s ramp restored
  76.8% this draw vs 98.8% booked).
- **PR-harvest fleet-wide:** "the judge must be independently implemented" is a recurring hard-won rule.

**Law proposal (speculation, but 7 witnesses):** before extending ANY scale axis, freeze the measure and
prove the gate can fail. Most INCONCLUSIVE verdicts this week were measurement-scoped, not thesis-scoped.

### P2 — Federation/modularity value lives only at structural blindness; aggregates hide it
- **COMP1:** the only passing gate is G1R-negation +0.126 CI[+0.034,+0.219] — exactly where the
  monolith's BoW sensor is structurally blind (polarity=word-order); monoliths sit BELOW regime chance
  (0.423/0.428 vs 0.50). Full-board FAIL. LA-v2's char-twin (shared blindness) bought +0.0017.
- **COMP0:** dilution localized to counting; semantic saturated for everyone (ceiling). COMP1 inverted
  into a floor (all arms 0.547–0.562 on 0.517 chance). Same disease, opposite sign: **aggregate boards
  compress in whichever direction the corpus is miscalibrated.**
- Echo: XP-A (independent failure modes = transfer), B1b per-region (deficit localized to deadzone/ramp,
  invisible in the pooled gate where saturation=88.4% of ticks dominates).

### P3 — Behaviour fidelity is cheap; exact-float fidelity is representational AND region-localized
- **B1-DISTILL:** direction 1.0000 on law-moving ticks, h2h 0.550 (control 0.5000 exact), but 1e-3
  agreement 0.057; 300-ep control 0.349 → gap partly representational.
- **B1b runB:** clamp = 1.0000 for EVERY arm at EVERY tolerance; ReLU pays only in saturation
  (+0.2895 @1e-2 = the whole aggregate +0.257); deadzone+ramp unmoved by ANY basis at 40ep (<0.50);
  τ₂=5e-2 optimization-bound (300-ep tanh control 0.9902). Both builds agree: learned-kink never beats tanh.
- **C1-PLAYTEST:** law 7/7 (9/9 with partials) vs the 7B; per-tick agreement 0.0917 — behavioural
  domination with zero rule violations. The law is behaviour-complete at pong.
- **FT-A1:** 1.2k-param MLP absorbs exact minimax 0.9996 (P1 FAIL-HIGH) — the "local-voting ceiling"
  was optimizer/label artifacts, not capacity. **A2:** linear doesn't collapse at 4×4.

**Pattern:** every "ceiling/knife-edge tolerance" claim this fleet tested dissolved into basis,
optimizer, or protocol artifacts when a tiny control ran. Tiny controls are the cheapest truth in the lab.

### P4 — Seats: completer ≠ verifier; determinism is a property of the serving window
- **G1:** 96/96 completion, blind verdict 0.5208 = chance (corrected 0.6979 < 0.75). xref 0.938 vs
  count 0.438 / contra 0.312 — retrieval strong, consistency inverse.
- **G1c routing table is the law now:** LOCAL xref/contra/count + JEV arith/date/seq + GLM escalation
  (0.8021/1.0000). **XP-C:** local 3B flips 1–3/30 per battery under co-tenancy; cloud 30/30; stub exact.
  **C1:** seat serialization (OLLAMA_MAX_LOADED_MODELS=1) is a hard co-tenancy law (ROADMAP doctrine #2).
- **HY4-TRIAL:** Hy4 wins fact-bearing authorship (0 fabricated vs 2✓/4✗) but costs 6.4× in / 4.7× out /
  1.27× cache-read — better at reasoning about cache economics, worse as a cache-read unit.

### P5 — Simple scaling laws keep surviving contact with the 4050
- **D12i/D12j (two-witness KEEP):** T_floor ~ C(N,p)/W survives to W=128; message floor T=2.
- **A5-PARITY:** bit-parity 0.0, 3.06G cells/s within 1.3% of receipt — our box is a legitimate
  conformance node for the fleet's hardware class (the "datacenter silicon" framing was wrong).

---

## 2. Highest-leverage next moves (BET / PROBE / KILL) — all 4050-falsifiable, <30 Wh

### MOVE 1 — COMPOSITE-2: VIEW as the manipulated variable, with a pre-calibrated mid-band corpus
- **BET:** federation's win is blindness-repair (P2). A polarity/position-aware sensor added to the
  federation reproduces the COMP1 negation pattern on a *different* blind regime; the router picks
  sensor-not-expert.
- **PROBE (~12 Wh, COMP1-shaped):** the make-or-break addition — **calibrate difficulty BEFORE arms
  run**: a linear probe must land boards in 0.65–0.85; make that a wiring gate (F-gate), else VOID.
  Arms: SINGLE / FED / FED+hetero-sensor; per-regime bootstrap CIs primary; full-board secondary.
  Gate: regime-localized CI-excl-0 win ≥ +0.08 on the pre-declared blind regime.
- **KILL:** no regime-localized hetero-sensor win on a mid-band board → retire the federation thesis
  (three strikes: COMP0 granularity, COMP1 floor, COMP2 blindness-repair) and demote LA to a D1b footnote.

### MOVE 2 — H5 measure repair by socket re-scope, THEN the 1000-world fire
- **BET:** D2-V1b's H1 FAIL is measure noise, not thesis death. On the stable sockets (reflex.orient
  det 1.000, policy.action 0.901, declared encoders, E3) the ρ CI narrows below 0.40.
- **PROBE (~0 Wh first):** re-analyze the EXISTING banked d2_v1 traces (54/54 runs, B=1000 bootstrap
  already on disk) on the stable-socket subset. Gate: CI width < 0.40 → fire 1000-world ×5 (~1.5 h,
  ~10–15 Wh) with the one-line receipt purpose ("halve ρ CI on a stable measure").
- **KILL:** stable-socket ρ CI stays wide or sign-flips → H1 dead at v1 scope; close D2's transfer
  claim, keep H3 (gap_mis − gap_sim = +0.1427) as the bookable law. Do NOT fire ×5 on an unstable
  measure — precision for an unmeasured construct is the exact COMP0/COMP1 disease.

### MOVE 3 — B1C per-region value-fidelity (already ROADMAP queue #1 — endorse with amended gates)
- **BET:** the value-fidelity gap is deadzone+ramp-local (B1b's structure) and closable by targeting,
  not by basis (all bases <0.50 there at 40ep; nothing basis-shaped works).
- **PROBE (~3 Wh, B1b-shaped):** 300 epochs, arms = tanh-ensemble / capacity×4 / deadzone-reweighted
  loss / binned targets, with **per-region gates primary** (deadzone ≥0.99 @5e-2, ramp ≥0.90) and the
  pooled gate secondary. Pin per-region thresholds in prereg BEFORE fire.
- **KILL:** nothing closes deadzone at 300ep → bank "law = behaviour-complete; value fidelity in
  deadzone is optimization-hard, basis-irrelevant" and close the B-line representation question.

### MOVE 4 — Instrument doctrine as executable artifact (near-zero Wh, highest ROI/min)
- **BET:** XP-A's split (invariants transfer 0.994, pins 0.000) generalizes at n≥6 instruments.
- **PROBE (CPU + pennies):** (a) adopt spread_vs_gap as 4th refusal class in tools/verdict_gate.py
  (already queued); (b) XP-A2 with ≥6 instruments (add digest-manifest checker, G7 field validator,
  typesafe JEV cell, schema-lint); gate rho ≥ 0.70 with permutation p reported.
- **KILL:** if invariant-based instruments stop transferring, the measurement-first doctrine itself
  dies honestly — that's a result worth having, and it would re-route MOVE 1–3's gate designs.

### MOVE 5 (hygiene, do regardless) — the PR-harvest probe cluster
Probes 4 (distinct-board re-eval, 2 min) and 7 (**our own ledger row-hash audit, 2 min — highest
internal value/min in the fleet**; our unkeyed, actor-unbound hash path is the cheapest fix we own),
then probes 1–3 as one bench day (~15 min GPU). Gate each per pr_harvest/SUMMARY.md.

---

## 3. STOP list — lanes returning INCONCLUSIVE for structural reasons

1. **Full-board aggregate federation gates.** COMP0 ceiling → COMP1 floor; aggregates compress in
   whichever direction the corpus is miscalibrated. Stop booking full-board as primary, ever.
2. **Firing D2 ×5 while H5 is unstable** (already frozen in QUEUE — reinforce: the trigger being "MET"
   on a failed measure is the trap).
3. **Static-pin instruments against unknown-failure classes** (XP-A arm A: 0.000 transfer). XP-A2 only
   with n≥6 instruments; at n=3 the rho gate is mathematically binary — structurally INCONCLUSIVE.
4. **Local-seat-as-verifier scoring.** 7B blind verdict = chance twice (0.5208 raw / 0.6979 corrected
   sound classes). Route verdicts per G1c table; stop re-measuring seat accuracy on adversarial classes.
5. **Knife-edge exact-float gates (1e-3) on kinked laws** — they measure basis+optimizer (B1/B1b,
   booked twice). Per-region or behaviour gates instead.
6. **Single-draw timing/slowdown claims without ramp receipts** (INSTRUMENT-01 repro: 76.8% vs 98.8%
   on the same protocol). Point estimates of GPU cost are banned by our own law — enforce it.
7. **Un-serialized seat lanes** (XP-C, C1 thrash): co-tenant model swaps are a guaranteed confound.
   Any seat lane that didn't serialize = structurally VOID-adjacent before it starts.

---

## 4. Wildcard from the PR-harvest (no current lane exploits it)

**Ring-attractor router.** The fly-CX cluster (chiaroscuro #4/#6, arcade #6) is the PR-harvest's only
PASS mechanism (flycx 4/4, 1:1 cross-project port): E-PG bump + per-tick ω integration + ternary
ψ (Commit/Reject/Abstain) + *conflict shrinks the belief vector*. No quilt-gpu lane uses it — our
routers are centroid-correlation (COMP0, saturated 1.0) or trained MLP (COMP1, held-out 0.7356,
top1-top2 gap 0.041 — finally ambiguous, finally interesting).

The connection (speculation, but two booked facts pointing at it): COMP1 says routing value lives
exactly where the sensor is blind/uncertain, and our router is *worst precisely there*. A
certainty-gated ring attractor is a training-free router whose Reject dynamics (belief shrinks on
conflict) is a natural uncertainty signal — i.e., an LA-trigger mechanism with a mechanism, not a
threshold.

- **PROBE A (~5 min, <1 Wh):** reproduce their convergence law on our box (convergence within 25% of
  mass/gain; v1 H1/H2 ±5 pts) — pr_harvest probe 1.
- **PROBE B (~12 Wh):** re-fire the COMP1 corpus with the trained router swapped for the ring router.
  Gates: (i) held-out routing accuracy ≥ trained router −0.02 with ZERO training; (ii) Reject-rate on
  the negation regime exceeds the all-regime mean by ≥2× (the ring "sees" the blind regime); (iii)
  FED+ring ≥ FED+trained on the blind regime board.
- **KILL:** ring routing < trained −0.05 or Reject-blindness absent → bank "attractor routing is a
  pong/paddle trick, not a corpus router" and stay with trained routers.
- Why this wildcard over KC/receipt-chains: KC sparsification is a receipted *negative* for discrete
  vocab (tells us where NOT to spend); receipt chains are our hygiene fix (MOVE 5/probe 7), not a
  science lane; the ring is the only machine with a live PASS and an unexploited slot in our stack.

---

## Bookkeeping
- Booked: this file + QUEUE.md line. NOT COMMITTED (lane rule; keeper commits).
- Energy: 0 Wh (read/synthesis only).

# est_freeze_interface

## WHAT IT IS

Six independent determinacy estimators behind **one validated interface**:

```python
score(records, spec, est="E3", weight="operational", seed=0, nperm=120)
    -> float in [0,1]
# spec = {"inp": record->hashable, "out": record->hashable, "O": int}
# weight ∈ {"operational", "uniform", "degenerate"}
```

A record set plus an input/output channel spec in; a [0,1] determinacy of
the output given the input out. The estimators are independent code paths:
**E0** plug-in conditional entropy + Miller-Madow (the prereg formula),
**E1** excess mode-agreement vs permutation floor, **E2**
effective-alphabet/coverage-width, **E3** permutation-exact normalized MI
bias-corrected (`1 − Hcond/Hcond_null`), **E4** split-half tick-parity TV
(seed-invariant), **E5** per-bin purity Wilson lower bound (pure bin →
exact 1.0).

The `seed=0` default is part of the frozen contract from the lane ("fix
the permutation seed (seed=0) so C2 is exactly 0 by construction") —
changing it would break interface-identical reproduction; this block's
own self-test data draws use the house seed 2718.

Also exports the **validation battery** the lane froze: `synthetic_atoms`
(C1 exactness), `noisy_channels` (bias vs analytic truth),
`stationary_control` (identical true determinacy under three input
distributions → spread = pure estimator instability), `sensitivity_socket`
(per-bin truth fixed but differing by bin → spread = genuine input
sensitivity), and `frozen_v1` (the conjunctive frozen criterion).

## WHY (the booked receipts)

- **EST-FREEZE** (RESULTS.md, 2026-10-01, lane EST-FREEZE / deepseek-v4-flash,
  prereg `proposals/runs/EST-freeze.md` frozen before any run): reproduced
  the D2 two-build disagreement EXACTLY with the same math (build B
  `salLevel→fire` 0.4455/0.4693, `salx→fire` 0.7227/0.9699; build A
  full-channel 1.0000) — **the divergence was the input ENCODER, not the
  measure.** Estimator×test verdicts: E0/E3 pass all but C3; E1 bias
  fail; E2 C3+C4 fail; E4 disqualified (atoms 0.998, bias 0.564); E5
  bias+stat fail.
- **FROZEN-V1 = NONE, honestly** — criterion C3 (spread ≤ 0.15 across
  operational/uniform/degenerate on real sockets) is unsatisfiable for
  all six; the stationary-truth control shows the good estimators
  contribute ≤ ~0.04 spread (E3 0.003–0.039), so the real spread is
  **genuine socket input-distribution sensitivity, not estimator bias**.
  H5 as written conflated the two — the prereg bug the shootout found.
- **Keeper fold**: measure pair frozen — **E3 primary, E0 reserve**;
  freeze declared encoders (the actual v1 blocker fix); H6 unblocked with
  the encoder frozen (reflex 1.000 − episodic 0.352 = 0.648 ≥ 0.5; build
  B's 0.118 was a pure encoder artifact). H5 re-derived: gate on the
  operational distribution, report per-socket spread as a datum with the
  synthetic floor subtracted, keep degenerate as an F4 diagnostic.

## PROPERTIES

- One signature, six implementations — swap `est=` and nothing else; the
  interface is the deliverable (the lane's whole point: "try different
  ways" behind one contract).
- Fail loud: unknown `est`/`weight` raises `ValueError` (as at source).
- Deterministic under the frozen permutation seed; E0/E2 have no RNG at
  all; E4 is seed-invariant by construction.
- The self-test gates a cross-data-seed seed-mean (stationary spread)
  with the frost law: **std == 0 ⇒ INCONCLUSIVE, never PASS**.
- stdlib + numpy, CPU-only, <1s for the whole battery.

## COMPOSITION

- **Measures any cell/trace lane**: D2 stochastic-worlds sockets
  (`results/d2_build/*_traces.json` shape: records + channel spec),
  reflex-vs-episodic determinacy (H6), or the determinacy of any block's
  outputs — e.g. score `exact_minimax_labels` boards under an encoder, or
  an `ie3_dedicated_trunks` cell's answers given its regime.
- **Encoder law travels with it**: always DECLARE the input channel
  (`spec["inp"]`) — an undeclared lossy projection is precisely what
  manufactured the D2 A/B disagreement this interface diagnosed.
- Frozen-pair usage: report E3, keep E0 as the reserve; anything else
  needs a fresh battery run (this block's self-test is the template).

## SELF-TEST

From the lab root, CPU-only, <1s:

```
python3 blocks/est_freeze_interface/block.py
```

(1) C1: frozen pair E3/E0 EXACTLY 1.000 on deterministic atoms O=2..6
(all six ≥ 0.99; E4's booked 0.998 is the disqualified one); (2) bias vs
analytic truth on noisy channels: frozen pair worst |err| ≤ 0.15 (booked
≈0.05; E1/E4/E5 booked 0.29/0.58/0.40 — reproduced as the battery table);
(3) stationary control O2 p=0.8 over 3 data seeds: frozen-pair mean
spread ≤ 0.08 (booked E3 0.003–0.039) with cross-seed std > 0 (frost law);
(4) the H5 conflation demonstrated: on the sensitivity socket (per-bin
truth fixed, differs by bin) E3 spread > 0.15 and the CONJUNCTIVE frozen
criterion returns **FROZEN-V1 = NONE** — the booked finding reproduced on
synthetic material; (5) H6-style range with a declared encoder ≥ 0.5;
(6) interface contracts: frozen-seed determinism, unknown est/weight
fail loud. Final stdout line is exactly one JSON object with one
top-level `"verdict"`; exit 0 iff PASS.

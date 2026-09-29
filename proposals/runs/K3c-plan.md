# K3c — Collapse diagnosis (not a boundary roll)

**Pre-registered 2026-09-29 07:10 AKDT, before any K3c code.** Status: pending fire.

## Why

K3 and K3b both went INVALID_HARNESS on the same frozen gates, and K3b added the
two facts that make another boundary roll pointless:

1. **The r=0.25 seed-42 poison replicated BIT-IDENTICALLY** across independent
   runs (state 3.111 / diff 3.079 in both K3 and K3b) — the collapse is
   deterministic given (mix draw, init, batch sequence), not training noise.
2. **At r=0.00 the dataset CONTENT is seed-independent** (pick < 0.0 never
   fires; only the shuffle and RNG-driven dynamics differ), yet seed 7's state
   arm collapsed (4.349) while seed 42's was fine (2.568) — a pure
   training-dynamics failure on identical data.

So the harness has a persistence-plateau escape problem affecting ~3/30 cells.
Until the collapse mode is understood, the boundary question (where diff beats
state) stays PARKED. K3c does not touch the boundary.

## Design (frozen)

Replicate the K1/K3/K3b training loop EXACTLY (TinyPredictor, AdamW lr 3e-4,
STEPS=1200, BATCH=64, same windowing, same scoring) with ONE addition:
**log train-batch MSE and full-val reconstruction MSE every 100 steps**, plus
**per-domain val MSE (synth half vs lavfi half of the fixed interleaved val)**.

Cells (6 trainings, ~2 min GPU):

| cell | r | seed | target | role |
|---|---|---|---|---|
| P1 | 0.25 | 42 | state | poisoned (K3+K3b identical) |
| P2 | 0.25 | 42 | diff | poisoned (K3+K3b identical) |
| P3 | 0.00 | 7 | state | poisoned (order-only draw) |
| C1 | 0.00 | 7 | diff | healthy control, SAME draw as P3 |
| C2 | 0.25 | 1337 | state | healthy control, same r as P1 |
| C3 | 0.00 | 42 | state | healthy control, r=0.0 sibling of P3 |

Persistence floor recomputed on the fixed val (expect ≈ 2.879 as in K3).

## Classification (frozen, informational — no KEEP/KILL)

- **no-learn**: final train-batch MSE ≥ 80% of its step-100 value (never leaves
  the persistence plateau).
- **train-val split**: final train-batch MSE < 50% of step-100 value AND final
  val MSE ≥ floor (learned the drawn train set, failed the fixed val).
- **domain split**: one domain half of val ≥ floor while the other < floor.
- **late loss**: val MSE dips then rises ≥ floor.
- **healthy**: final val MSE < floor.

Output: `training/keel_k1/results/k3c_diagnose.json` + per-100-step curves in
the log. Booking: informational entry in RESULTS.md — K3c diagnoses, it does
not vote on the boundary. Any future boundary attempt (K3d) requires a NEW
pre-registration that addresses the collapse mode K3c finds.

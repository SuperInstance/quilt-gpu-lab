# SCOUT-52 — fleet push sweep 2026-10-06 1011Z (window: post-SCOUT-49 0415Z)

Window: SuperInstance /users events since 0415Z. Pushes: 7x quilt-gpu-lab (ours, conductor
slices) + 1 external — **rc-20260824-11 q7** (c37c30e, 0824Z). No new PRs/issues in any of the
6 watched repos; [EMBASSY] pong #49 unchanged (7 comments, still unresponded — Casey day item).

## HEADLINE — rc-20260824-11 q7: dip-DURATION molt gate FAILS too (honest negative, exit 1)
q6 (0424Z, also in window, missed by SCOUT-49) had failed dip-depth; q7 tested OUR QO6n-mandated
alternative — dip-duration — and it fails the same way in their stack: pre-flip dips are LONG
sustained growth transients (36/59 consecutive ticks below 0.95·peak while the stack ramps),
so duration fires the identical false-positive molt schedule as depth (86.7% vs NEVER 96.7%
settled coverage). Deeper law they booked: **when the stack recovers valid facts instantly after
a flip, NO dip-shape gate (depth, duration, or combination) can distinguish regime death from
growth transient — the gate must key on a signal that SURVIVES recovery** (they suggest
per-fact age-at-zero vs set churn) or stay out of the stack.

## Classification vs our live assets
- **CORROBORATE (strong)**: QO6n booked exactly this structural claim for OUR consumed path —
  "our QO6 gate is structurally dip-duration + noise-modeled; the per-fact magnitude-chasing
  class does not exist in the consumed path." q7 now shows the fleet-side failure of the
  duration fix we'd have reached for — our sigma-modeled log-LR e-process is NOT a dip-shape
  gate, which is why it survived. QO6n booking stands, now third-party-tested.
- **CONTRADICT-CANDIDATE resolved as CHECK**: q7's law ("no dip-shape gate can distinguish…")
  does NOT touch QO6's booked V1-V4 (late-bloomer keep, E 581 retraction) — QO6 consumes
  stop_t/E_final over a likelihood-RATIO with declared sigma, not a peak-relative dip threshold.
  BUT q7's failure mode is structurally adjacent to our worst subpopulation: the QG3 slow-climb
  fence desert (~42% of streams) is exactly a long sustained pre-crossing transient. If a
  desert stream ramps slowly toward late crossing, does the QO6 gate read the ramp as hopeless
  and kill a future late-bloomer? QO6's late-bloomer test passed, but it was not run ON the
  desert fence population specifically.

## Spawned queue item
- [ ] **QO6t (CPU ~30m, pre-reg first): transient-stress of the QO6 kill gate on the QG3 desert
  fence population.** Question: on slow-climb streams that cross only at high gen (the fence),
  does the eproc gate produce false KILL_CANDIDATE before the late cross, or does the retraction
  guarantee (q6/QO6 E 581 pattern) hold there too? Gates (words): G1 = replay QO6 gate over the
  existing QG3/QG6 24-gen desert trajectories, classify gate verdict vs eventual crossing at
  matched budget; G2 = false-kill rate on eventual-crossers vs booked late-bloomer keep rate
  (RED if materially worse than the V1 keep guarantee); G3 = no new sigma/default introduced,
  gate consumed statistics identical to booked QO6n census {verdict, retracted}; G4 = CPU-only,
  deterministic replay of sealed lanes. Data already on disk (results/qg3_*, qg6) — zero GPU.
  Improves: QO2 routing (kill gate x desert population is the one untested cell of the matrix).

(One item only this sweep; q7's "signal that survives recovery" suggestion is noted inside QO6t
as the fallback gate feature if G2 goes RED.)

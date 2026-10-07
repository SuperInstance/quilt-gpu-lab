# QO6s — good→bad retention asymmetry on the frozen QO6 kill gate

Spawned by SCOUT-55 (2026-10-06): rc-20260824-11 q11 (ledger memory horizon) names the
COMPLEMENTARY failure mode to QO6h's q10. QO6h proved evidence-expiry is structurally
impossible (full-prefix cumsum, horizon==t). But that same construction means a
good→bad flip mid-stream leaves E dominated by the confirming prefix — the kernel may
be UNABLE to kill within any reasonable post-flip latency. QO6 only tested bad→good
(late bloomers, V2); QO6t covers transient stress; neither covers sustained decay.

## Question
On the frozen tools/eproc.py kernel, does the kill gate fire within a pre-registered
decision-latency budget after a good→bad flip, or does the confirming prefix drown
the kill evidence (retention-asymmetry limit of the QO2 kill matrix)?

## Streams (constructed, deterministic, no RNG)
All claims DECREASES; sigma pre-registered here; witness refusal rules inherited
(sigma required, >=10 samples, non-finite refuse — fail-loud).
- GB1: 30-step rising prefix (0.20 → 0.60, KEEP direction) then V3-style hopeless
  decay (-0.06/step x 40). sigma=0.03, delta=0.05 (V3's pins). Flip at t=30.
- GB2: same tail, 60-step rising prefix (0.20 → 0.60, +2/30... verbatim: linear rise
  to 0.60 over 60). Flip at t=60. sigma=0.03, delta=0.05.
- GB3: short prefix — 15-step rise — same tail. Flip at t=15. sigma=0.03, delta=0.05.
Controls (frozen kernel replays, verbatim constructions from qo6h file):
- CTRL-KILL: V3 hopeless (expect KILL_CANDIDATE — kernel sanity).
- CTRL-KEEP: V2 bloom (expect KEEP/retraction side intact).

## Pre-registered gates (words, frozen before fire)
- G1 (control): CTRL-KILL decision == KILL_CANDIDATE.
- G2 (control): CTRL-KEEP decision == KEEP.
- G3 (PRIMARY): for EVERY GB stream, decision == KILL_CANDIDATE AND
  stop_t <= flip_t + 15 (LATENCY_BUDGET=15 samples, chosen pre-hoc as ~2x the
  kernel's own min-witness window; not tuned post hoc).
- VERDICT PASS if G1-G3 all hold. If ANY GB stream never kills or exceeds budget:
  VERDICT RED — the retention-asymmetry limit is NAMED. RED does NOT void QO6/QO6h/
  QO6t (different stream class, those bookings tested other cells) but enters the
  QO2 kill matrix as a known-limit row. NO re-roll, NO sigma tuning to flip verdict.

## Cost
CPU, deterministic, seconds. Scratch out via --out (RC-1 doctrine).

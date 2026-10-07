# QO7a — Deficit-WINDOW alignment law (pre-reg amendment for QO7)

Spawned: SCOUT-61 slice (2026-10-07 ~07:2x AKDT), conductor (B) slot.
Source: SuperInstance rc-20260824-11 q10–q14 gate-negative series (q14 commit 58e1f54):
the reward-dip reflex fires 94/94 PRE-flip — on the growth transient — and is silent in
the only window the deficit actually exists. A gate that fires where there is no deficit
is dead weight at best.

## Amendment (applies when QO7's pre-reg is drafted; QO7 remains a Casey day-item)

QO7's routing/e-process gates (oracle kill/keep thresholds, budget triage, eproc gate)
MUST be scored on **coverage gained DURING the deficit window**, not on firing count.

Definitions for the scoreboard:
- **Deficit window** (per stream): the interval between the first observation at which
  the QO2 oracle could in principle separate the outcome and the terminal event
  (crossing at gens=24, or kill decision point). For late-bloomers this is
  [g1, crossed_gen); for hopeless streams [g1, budget exhaustion).
- **Aligned firing**: a gate action (keep-extension, kill, hold) that lands inside a
  stream's deficit window AND changes the resource allocation relative to no-gate.
- **Misaligned firing**: any firing outside the deficit window (pre-flip class —
  the rc q14 pattern; reflexes that fire on the growth transient score RED here).

Verdict rule: a gate with high firing count but zero aligned-coverage delta is scored
**RED (dead-weight class)** even if every firing is individually "correct" post hoc.
Firing counts are reported but never a pass criterion.

## Corroboration booked into this law

- rc q10–q13: molt/refill channel closed under every tested observable/retention/reflex
  source → CORROBORATE of QG6 (intervention inert on this stack family).
- Our QO6s booking (2026-10-06 19:1x, retention asymmetry): good→bad streams can never
  be killed by prefix evidence — the kill gate's value is entirely in its deficit-window
  alignment, since its misaligned-firing cost (killing a recoverable stream) is the
  expensive error. QO7's cost matrix must weight misaligned kills ≥ misaligned keeps.

Cite: rc 58e1f54 (q14), our QO6s booking, SCOUT-61 full note.

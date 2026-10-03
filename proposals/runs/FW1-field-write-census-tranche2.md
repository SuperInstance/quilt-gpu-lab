# FW-1 Field-Write Census — TRANCHE 2 (pre-registered before analysis committed)

Pre-reg committed BEFORE findings booking. Method identical to tranche 1
(proposals/runs/FW1-field-write-census-tranche1.md): for each BOOKED verdict, enumerate the
state fields the verdict reads, grep every write site in the producing tool + imports; a
verdict-feeding write path unexercised by a committed test or verified repro = RED.

Targets (per 16:4x tranche plan): D12i, W5b2, QG7 (ensemble booking).

## Pre-registered classification rules
- GREEN: all verdict-feeding write paths internal to committed code AND covered by booked
  repro/replicate/ensemble.
- YELLOW: no uncovered write path, but coverage is verdict-level only under known
  nondeterminism (must be already booked as such).
- RED: a write path feeding a verdict field that no committed test or booked run exercises.
- Static analysis only this slice (no GPU fires; lane policy: one at a time, idle lane not
  spent on a census).
